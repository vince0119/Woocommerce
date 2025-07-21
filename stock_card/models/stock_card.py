from odoo import models, fields, api
from datetime import datetime

class StockCard(models.Model):
    _name = 'stock.card'
    _inherit = ['mail.thread']

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    location_ids = fields.Many2many('stock.location', string='Locations')
    name = fields.Char(string='Name')
    notes = fields.Text(string='Notes')
    sequence = fields.Integer(string='Sequence', default=1)
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
    ], string='State', default='draft')
    stock_card_line_count = fields.Integer(string='Stock Card Line Count', compute='_compute_stock_card_line_count')
    active = fields.Boolean(string='Active', default=True)

    def action_refresh(self):
        for record in self:
            record.stock_card_line_ids.unlink()
            lines_data = self.genReportLines(
                record.id,
                record.company_id.currency_id.id,
                record.location_ids.ids,
                record.start_date,
                record.end_date,
                record.company_id.id
            )
            for line in lines_data:
                self.env['stock.card.line'].create({
                    'stock_card_id': record.id,
                    'product_id': line['product_id'],
                    'category_id': line['category_id'],
                    'uom_id': line['uom_id'],
                    'location_id': line['location_id'],
                    'qty_start': line['qty_start'],
                    'qty_in': line['qty_in'],
                    'qty_out': line['qty_out'],
                    'qty_end': line['qty_end'],
                    'val_start': line['val_start'],
                    # Thêm các trường khác nếu cần
                })

            return {
                'type': 'ir.actions.act_window',
                'res_model': 'stock.card',
                'res_id': record.id,
                'view_mode': 'form',
                'view_type': 'form',
                'view_id': self.env.ref('stock_card.view_stock_card_form').id,
                'target': 'current',
                'flags': {
                    'form': {'action_buttons': True}
                }
            }

    def _compute_stock_card_line_count(self):
        for record in self:
            record.stock_card_line_count = self.env['stock.card.line'].search_count([
                ('stock_card_id', '=', record.id)
            ])

    def action_open_stock_card_line(self):
        self.ensure_one()
        return {
            'name': 'Stock Card Lines',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.card.line',
            'view_mode': 'tree',
            'domain': [('stock_card_id', '=', self.id)],
            'context': dict(self.env.context),
            'target': 'current',
        }

    def _compute_valuation_val(self, stock_card_lines=None):
        if stock_card_lines is None:
            stock_card_lines = self.env['stock.card.line']

        for rec in stock_card_lines:
            base_domain = [
                ('product_id', '=', rec.product_id.id),
                ('date', '>=', rec.stock_card_id.start_date),
                ('date', '<=', rec.stock_card_id.end_date),
                ('state', '=', 'done'),
                ('company_id', '!=', False)
            ]

            # Separate domains for inbound and outbound moves
            domain_val_in = base_domain + [('location_dest_id', '=', rec.location_id.id)]
            domain_val_out = base_domain + [('location_id', '=', rec.location_id.id)]

            # Perform search only once and use generators for summation
            stock_move_model = rec.env['stock.move.line']

            val_in = sum(stock_move_model.search(domain_val_in).mapped('in_out_amt'))
            # val_in = 0
            val_out = sum(stock_move_model.search(domain_val_out).mapped('in_out_amt'))

            # Assign results to the record
            val_in = abs(val_in)
            val_out = abs(val_out)

            valuation_layer_model = rec.env['stock.valuation.layer']

            valuation_domain = [
                ('product_id', '=', rec.product_id.id),
                ('stock_move_id', '=', False),
                ('create_date', '>=', rec.stock_card_id.start_date),
                ('create_date', '<=', rec.stock_card_id.end_date),
                ('company_id', '=', rec.stock_card_id.company_id.id)
            ]

            valuation_layers = valuation_layer_model.search(valuation_domain)

            for layer in valuation_layers:
                if layer.value < 0:
                    val_out -= abs(layer.value)
                elif layer.value > 0:
                    val_in += abs(layer.value)

            rec['val_in'] = val_in or 0
            rec['val_out'] = val_out or 0

            rec['val_end'] = rec.val_start + val_in - val_out
            rec['val_variation'] = val_in - val_out

    def genReportLines(self, REPORT_ID, CURRENCY_ID, LOCATION_ID, START_DATE, END_DATE, COMPANY_ID, ADDITIONAL=""):
        # LOCATION_ID = 8
        NOW_DATE = '2052-12-31'

        opts = {
            "REPORT_ID": REPORT_ID,
            "LOCATION_ID": LOCATION_ID,
            "CURRENCY_ID": CURRENCY_ID,
            "START_DATE": START_DATE,
            "END_DATE": END_DATE,
            "NOW_DATE": NOW_DATE,
            "COMPANY_ID": COMPANY_ID,
            "ADDITIONAL": ADDITIONAL
        }

        opts['QUERY_MOVELINE'] = """
            SELECT
                stock_move_line.date,
                stock_move_line.product_id,
                stock_move_line.lot_id,
                stock_move_line.quantity,
                stock_move_line.product_uom_id,
                stock_move_line.location_id,
                stock_move_line.location_dest_id,
                (
                    COALESCE(
                        CASE
                            WHEN (stock_move_line.location_dest_id = {LOCATION_ID}) THEN (
                                COALESCE(stock_move_line.quantity * COALESCE(_product_uom.factor/_move_uom.factor, 1), 0)
                            )
                        END,
                        0
                    )
                ) AS qty_in,
                (
                    COALESCE(
                        CASE
                            WHEN (stock_move_line.location_id = {LOCATION_ID}) THEN (
                                COALESCE(stock_move_line.quantity * COALESCE(_product_uom.factor/_move_uom.factor, 1), 0)
                            )
                        END,
                        0
                    )
                ) AS qty_out,
                _stock_move.in_out_amt as price_unit
            FROM
                stock_move_line
            LEFT OUTER JOIN product_product on product_product.id = stock_move_line.product_id
            LEFT OUTER JOIN product_template on product_template.id = product_product.product_tmpl_id
            LEFT OUTER JOIN uom_uom _product_uom on _product_uom.id = product_template.uom_id
            LEFT OUTER JOIN uom_uom _move_uom on _move_uom.id = stock_move_line.product_uom_id
            LEFT OUTER JOIN stock_move _stock_move ON _stock_move.id = stock_move_line.move_id
            WHERE
                (
                    stock_move_line.location_dest_id IN ({LOCATION_ID})
                    OR stock_move_line.location_id IN ({LOCATION_ID})
                )
                AND stock_move_line.state = 'done'
                AND stock_move_line.company_id IN ({COMPANY_ID})
                {ADDITIONAL}
        """.format(**opts)

        opts['QUERY_IN_OUT'] = """
            SELECT
                l.*,
                (
                    COALESCE(
                        CASE
                            WHEN ((l.date >= '{START_DATE}') AND (l.date <= '{END_DATE}')) 
                            THEN (
                                l.qty_in
                            )
                        END,
                        0
                    )
                ) AS qty_in_period,
                (
                    COALESCE(
                        CASE
                            WHEN ((l.date >= '{START_DATE}') AND (l.date <= '{END_DATE}'))
                            THEN (
                                l.qty_out
                            )
                        END,
                        0
                    )
                ) AS qty_out_period,
                (
                    COALESCE(
                        CASE
                            WHEN l.date >= '{END_DATE}' THEN (
                                l.qty_in
                            )
                        END,
                        0
                    )
                ) AS qty_in_now,
                (
                    COALESCE(
                        CASE
                            WHEN l.date >= '{END_DATE}' THEN (
                                l.qty_out
                            )
                        END,
                        0
                    )
                ) AS qty_out_now
            FROM
                ({QUERY_MOVELINE}) AS l

        """.format(**opts)

        opts['QUERY_QUANTITIES'] = """
            SELECT
                product_id,
                SUM(m.qty_in_period) AS qty_in,
                SUM(m.qty_out_period) AS qty_out,
                SUM(m.qty_in_now) AS qty_in_todate,
                SUM(m.qty_out_now) AS qty_out_todate,
                0 AS qty_available,
                sum(m.price_unit) AS price_unit
            FROM
                ({QUERY_IN_OUT}) AS m
            GROUP BY
                product_id
        """.format(**opts)

        opts['QUERY_QUANTS'] = """
            SELECT
                product_id,
                0 AS qty_in,
                0 AS qty_out,
                0 AS qty_in_todate,
                0 AS qty_out_todate,
                SUM(quantity) AS qty_available,
                NULL AS price_unit
            FROM
                stock_quant
            WHERE
                location_id = {LOCATION_ID}
                AND stock_quant.company_id IN ({COMPANY_ID})
            GROUP BY
                product_id
        """.format(**opts)

        opts['QUERY_REPORT'] = """
            SELECT
                product_id,
                SUM(qty_in) AS qty_in,
                SUM(qty_out) AS qty_out,
                SUM(qty_in_todate) AS qty_in_todate,
                SUM(qty_out_todate) AS qty_out_todate,
                SUM(qty_available) AS qty_available,
                sum(COALESCE(price_unit, 0)) AS avg_price_unit
            FROM
                (
                    (
                        {QUERY_QUANTITIES}
                    ) 
                    UNION ALL
                    (
                        {QUERY_QUANTS}
                    )
                ) AS "unified"
            GROUP BY
                product_id
        """.format(**opts)
        opts['QUERY_FINAL'] = """
            SELECT
                {REPORT_ID} AS stock_card_id,
                report.product_id AS product_id,
                product_template.categ_id AS category_id,
                product_template.uom_id AS uom_id,
                {LOCATION_ID} AS location_id,
                {CURRENCY_ID} AS currency_id,
                ir_property.value_float AS standard_cost,
                (qty_available - (qty_in_todate - qty_out_todate) - (qty_in - qty_out)) AS qty_start,
                qty_in AS qty_in,
                qty_out AS qty_out,
                (qty_available - (qty_in_todate - qty_out_todate)) AS qty_end,
                (qty_in - qty_out) AS qty_variation,
                COALESCE((qty_available - (qty_in_todate - qty_out_todate) - (qty_in - qty_out))  * ir_property.value_float , 0) AS val_start
                --  COALESCE((qty_available - (qty_in_todate - qty_out_todate)) * ir_property.value_float , 0) AS val_end,
                --  COALESCE((qty_in - qty_out) * ir_property.value_float , 0) AS val_variation
            FROM
                ({QUERY_REPORT}) AS report
            LEFT OUTER JOIN product_product on product_product.id = report.product_id
            LEFT OUTER JOIN product_template on product_template.id = product_product.product_tmpl_id
            LEFT OUTER JOIN ir_property on ir_property.res_id = 'product.product,' || report.product_id
        """.format(**opts)

        query = opts['QUERY_FINAL'].format(**opts)
        self.env.cr.execute(query)
        res = self.env.cr.dictfetchall()

        return res

    def refreshReport(self):
        for report in self:
            REPORT_ID = report.id
            CURRENCY_ID = report.company_id.currency_id.id
            START_DATE = report.start_date
            END_DATE = datetime.combine(report.end_date, datetime.max.time())
            COMPANY_ID = report.company_id.id  # Get company ID
            locations = report.location_ids

            if len(locations) == 0:
                return False

            lines = []
            for location in locations:
                LOCATION_ID = location.id
                lines += self.genReportLines(
                    REPORT_ID,
                    CURRENCY_ID,
                    LOCATION_ID,
                    START_DATE,
                    END_DATE,
                    COMPANY_ID
                )

            self.env['stock.card.line'].search([('stock_card_id', '=', report.id)]).unlink()
            stock_card_line = self.env['stock.card.line'].create(lines)
            self._compute_valuation_val(stock_card_line)