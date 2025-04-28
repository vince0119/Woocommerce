from odoo import models, fields, api, _


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.onchange('identification_id', 'ssnid')
    def _onchange_check_duplicate_fields(self):
        current_record_id = self._origin.id or 0

        if self.identification_id:
            existing_ident = self.env['hr.employee'].search([
                ('identification_id', '=', self.identification_id),
                ('id', '!=', current_record_id)
            ], limit=1)
            if existing_ident:
                company_name = existing_ident.company_id.name if existing_ident.company_id else 'Unknown'
                warning_msg = (
                    f"Identification ID '{self.identification_id}' already exists in the Company: {company_name})"
                )
                return {
                    'warning': {
                        'title': "Duplicate Identification ID Warning",
                        'message': warning_msg
                    }
                }

        if self.ssnid:
            existing_ssn = self.env['hr.employee'].search([
                ('ssnid', '=', self.ssnid),
                ('id', '!=', self.id)
            ], limit=1)
            if existing_ssn:
                company_name = existing_ident.company_id.name if existing_ident.company_id else 'Unknown'
                warning_msg = (
                    f"SSN ID '{self.ssnid}' already exists in the Company: {company_name}"
                )
                return {
                    'warning': {
                        'title': "Duplicate SSN ID Warning",
                        'message': warning_msg
                    }
                }

        return {}
