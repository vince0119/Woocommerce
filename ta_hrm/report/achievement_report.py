from odoo import api, models, fields

class SaleAchievementReport(models.Model):
    _inherit = 'sale.commission.achievement.report'

    amount = fields.Integer(string="Amount", readonly=True)

    @property
    def _table_query(self):
        users = self.env.context.get('commission_user_ids', [])
        if users:
            users = self.env['res.users'].browse(users).exists()
        teams = self.env.context.get('commission_team_ids', [])
        if teams:
            teams = self.env['crm.team'].browse(teams).exists()
        return f"""
WITH {self._commission_lines_query(users=users, teams=teams)}
SELECT
    ROW_NUMBER() OVER (ORDER BY era.date_from DESC, era.id) AS id,
    era.id AS target_id,
    cl.user_id AS user_id,
    cl.team_id AS team_id,
    cl.achieved AS achieved,
    cl.amount AS amount,
    cl.currency_id AS currency_id,
    cl.company_id AS company_id,
    cl.plan_id,
    cl.related_res_model,
    cl.related_res_id,
    cl.date AS date
FROM commission_lines cl
JOIN sale_commission_plan_target era
    ON cl.plan_id = era.plan_id
    AND cl.date >= era.date_from
    AND cl.date <= era.date_to
"""

    @api.model
    def _select_invoices(self):
        return f"""
          MAX(rules.user_id) AS user_id,
          MAX(am.team_id) AS team_id,
          rules.plan_id,
          SUM({self._get_invoice_rates_product()}) AS achieved,
          SUM(CASE
              WHEN rules.qty_invoiced_rate > 0 AND (rules.product_id IS NULL OR rules.product_id = aml.product_id)
              THEN aml.quantity
              ELSE 0
          END)::integer AS amount,
          MAX(rules.currency_id) AS currency_id,
          MAX(am.date) AS date,
          MAX(rules.company_id) AS company_id,
          am.id AS related_res_id,
          'account.move' AS related_res_model
        """

    @api.model
    def _select_sales(self):
        return f"""
          MAX(rules.user_id) AS user_id,
          MAX(rules.team_id) AS team_id,
          rules.plan_id,
          SUM({self._get_sale_rates_product()}) AS achieved,
          SUM(CASE
              WHEN rules.qty_sold_rate > 0 AND (rules.product_id IS NULL OR rules.product_id = sol.product_id)
              THEN sol.qty_delivered
              ELSE 0
          END)::integer AS amount,
          MAX(rules.currency_id) AS currency_id,
          MAX(so.date_order) AS date,
          MAX(rules.company_id) AS company_id,
          so.id AS related_res_id,
          'sale.order' AS related_res_model
        """

    @api.model
    def _get_sale_rates_product(self):
        return """
            CASE
                WHEN rules.amount_sold_rate > 0 THEN rules.amount_sold_rate * sol.price_subtotal / so.currency_rate
                ELSE 0
            END
        """

    @api.model
    def _get_invoice_rates_product(self):
        return """
            CASE
                WHEN rules.amount_invoiced_rate > 0 THEN rules.amount_invoiced_rate * aml.price_subtotal / am.invoice_currency_rate
                ELSE 0
            END
        """

    def _invoices_lines(self, users=None, teams=None):
        return f"""
invoices_rules AS (
    SELECT
        COALESCE(scpu.date_from, scp.date_from) AS date_from,
        COALESCE(scpu.date_to, scp.date_to) AS date_to,
        scpu.user_id AS user_id,
        scp.team_id AS team_id,
        scp.id AS plan_id,
        scpa.product_id,
        scpa.product_categ_id,
        scp.company_id,
        scp.currency_id,
        scp.user_type = 'team' AS team_rule,
        {self._rate_to_case(self._get_invoices_rates())}
        {self._select_rules()}
    FROM sale_commission_plan_achievement scpa
    JOIN sale_commission_plan scp ON scp.id = scpa.plan_id
    JOIN sale_commission_plan_user scpu ON scpa.plan_id = scpu.plan_id
    WHERE scp.active
      AND scp.state = 'approved'
      AND scpa.type IN ({','.join("'%s'" % r for r in self._get_invoices_rates())})
    {'AND scpu.user_id in (%s)' % ','.join(str(i) for i in users.ids) if users else ''}
), invoice_commission_lines_team AS (
    SELECT
        {self._select_invoices()}
    FROM invoices_rules rules
         {self._join_invoices()}
    WHERE {self._where_invoices()}
      AND rules.team_rule
      AND am.team_id = rules.team_id
    {'AND am.team_id in (%s)' % ','.join(str(i) for i in teams.ids) if teams else ''}
      AND am.date BETWEEN rules.date_from AND rules.date_to
      AND (rules.product_id IS NULL OR rules.product_id = aml.product_id)
      AND (rules.product_categ_id IS NULL OR rules.product_categ_id = pt.categ_id)
    GROUP BY
        am.id,
        rules.plan_id
), invoice_commission_lines_user AS (
    SELECT
        {self._select_invoices()}
    FROM invoices_rules rules
         {self._join_invoices()}
    WHERE {self._where_invoices()}
      AND NOT rules.team_rule
      AND am.invoice_user_id = rules.user_id
    {'AND am.invoice_user_id in (%s)' % ','.join(str(i) for i in users.ids) if users else ''}
      AND am.date BETWEEN rules.date_from AND rules.date_to
      AND (rules.product_id IS NULL OR rules.product_id = aml.product_id)
      AND (rules.product_categ_id IS NULL OR rules.product_categ_id = pt.categ_id)
    GROUP BY
        am.id,
        rules.plan_id
), invoice_commission_lines AS (
    SELECT * FROM invoice_commission_lines_team
    UNION ALL
    SELECT * FROM invoice_commission_lines_user
)""", 'invoice_commission_lines'

    def _sale_lines(self, users=None, teams=None):
        return f"""
sale_rules AS (
    SELECT
        COALESCE(scpu.date_from, scp.date_from) AS date_from,
        COALESCE(scpu.date_to, scp.date_to) AS date_to,
        scpu.user_id AS user_id,
        scp.team_id AS team_id,
        scp.id AS plan_id,
        scpa.product_id,
        scpa.product_categ_id,
        scp.company_id,
        scp.currency_id,
        scp.user_type = 'team' AS team_rule,
        {self._rate_to_case(self._get_sale_rates())}
        {self._select_rules()}
    FROM sale_commission_plan_achievement scpa
    JOIN sale_commission_plan scp ON scp.id = scpa.plan_id
    JOIN sale_commission_plan_user scpu ON scpa.plan_id = scpu.plan_id
    WHERE scp.active
      AND scp.state = 'approved'
      AND scpa.type IN ({','.join("'%s'" % r for r in self._get_sale_rates())})
    {'AND scpu.user_id in (%s)' % ','.join(str(i) for i in users.ids) if users else ''}
), sale_commission_lines_team AS (
    SELECT
        {self._select_sales()}
    FROM sale_rules rules
    {self._join_sales()}
    JOIN product_product pp
      ON sol.product_id = pp.id
    JOIN product_template pt
      ON pp.product_tmpl_id = pt.id
    WHERE rules.team_rule
      AND so.team_id = rules.team_id
    {'AND so.team_id in (%s)' % ','.join(str(i) for i in teams.ids) if teams else ''}
    {self._where_sales()}
    GROUP BY
        so.id,
        rules.plan_id
), sale_commission_lines_user AS (
    SELECT
        {self._select_sales()}
    FROM sale_rules rules
    {self._join_sales()}
    JOIN product_product pp
      ON sol.product_id = pp.id
    JOIN product_template pt
      ON pp.product_tmpl_id = pt.id
    WHERE NOT rules.team_rule
      AND so.user_id = rules.user_id
    {'AND so.user_id in (%s)' % ','.join(str(i) for i in users.ids) if users else ''}
      {self._where_sales()}
    GROUP BY
        so.id,
        rules.plan_id
), sale_commission_lines AS (
    SELECT * FROM sale_commission_lines_team
    UNION ALL
    SELECT * FROM sale_commission_lines_user
)""", 'sale_commission_lines'

    def _achievement_lines(self, users=None, teams=None):
        return f"""
achievement_commission_lines AS (
    SELECT
        sca.user_id,
        sca.team_id,
        scp.id AS plan_id,
        CASE
            WHEN scpa.type IN ('amount_invoiced', 'amount_sold')
            THEN sca.currency_rate * sca.amount * scpa.rate
            ELSE 0
        END AS achieved,
        0::integer AS amount,
        scp.currency_id,
        sca.date,
        scp.company_id,
        sca.id AS related_res_id,
        'sale.commission.achievement' AS related_res_model
    FROM sale_commission_achievement sca
    JOIN sale_commission_plan scp ON scp.company_id = sca.company_id
    JOIN sale_commission_plan_achievement scpa ON scpa.plan_id = scp.id
    JOIN sale_commission_plan_user scpu ON scpu.plan_id = scp.id
    WHERE scp.active
      AND scp.state = 'approved'
      AND sca.type = scpa.type
      AND CASE
            WHEN scp.user_type = 'person' THEN sca.user_id = scpu.user_id
            ELSE sca.team_id = scp.team_id
      END
    {'AND sca.user_id in (%s)' % ','.join(str(i) for i in users.ids) if users else ''}
    {'AND sca.team_id in (%s)' % ','.join(str(i) for i in teams.ids) if teams else ''}
)""", 'achievement_commission_lines'