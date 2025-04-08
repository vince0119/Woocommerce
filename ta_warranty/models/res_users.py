from odoo import models, fields, api
import secrets


class ResUsers(models.Model):
    _inherit = 'res.users'

    token_seri = fields.Char('Token For Serial')

    def generate_api_token(self):
        self.ensure_one()
        self.token_seri = secrets.token_hex(16)
        return True

    @api.model_create_multi
    def create(self, vals):
        user = super(ResUsers, self).create(vals)
        if user.has_group('base.group_public'):
            user.generate_api_token()
        return user