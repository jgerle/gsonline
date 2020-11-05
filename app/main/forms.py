from flask import request
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, HiddenField, SelectField, IntegerField
from wtforms.validators import ValidationError, DataRequired, Length, InputRequired
from flask_babel import _, lazy_gettext as _l
from app.models import User


class EditProfileForm(FlaskForm):
    username = StringField(_l('Username'), validators=[DataRequired()])
    about_me = TextAreaField(_l('About me'),
                             validators=[Length(min=0, max=140)])
    submit = SubmitField(_l('Submit'))

    def __init__(self, original_username, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=self.username.data).first()
            if user is not None:
                raise ValidationError(_('Please use a different username.'))


class EmptyForm(FlaskForm):
    submit = SubmitField('Submit')


class PostForm(FlaskForm):
    post = TextAreaField(_l('Say something'), validators=[DataRequired()])
    submit = SubmitField(_l('Submit'))


class SearchForm(FlaskForm):
    q = StringField(_l('Search'), validators=[DataRequired()])

    def __init__(self, *args, **kwargs):
        if 'formdata' not in kwargs:
            kwargs['formdata'] = request.args
        if 'csrf_enabled' not in kwargs:
            kwargs['csrf_enabled'] = False
        super(SearchForm, self).__init__(*args, **kwargs)


class MessageForm(FlaskForm):
    message = TextAreaField(_l('Message'), validators=[
        DataRequired(), Length(min=1, max=140)])
    submit = SubmitField(_l('Submit'))

##
## OpenGS
##

class OpenGsGenericFlaskForm(FlaskForm):
    name = StringField(_l('Name / Bezeichnung'), validators=[DataRequired()])
    description = TextAreaField(_l('Beschreibung'), validators=[DataRequired()])
    dom_id = HiddenField("", validators=[DataRequired()])
    submit = SubmitField(_l('Hinzufügen'))

class OpenGsInfodomainForm(FlaskForm):
    name = StringField(_l('Name / Bezeichnung'), validators=[DataRequired()])
    description = TextAreaField(_l('Beschreibung'), validators=[DataRequired()])
    org_id = HiddenField("", validators=[DataRequired()])
    submit = SubmitField(_l('Hinzufügen'))

class OpenGsOrganizationForm(FlaskForm):
    name = StringField(_l('Name / Bezeichnung'), validators=[DataRequired(), Length(max=128)])
    description = TextAreaField(_l('Beschreibung (max. 128 Zeichen)'), validators=[Length(min=0,max=128)])
    user_id = HiddenField("", validators=[DataRequired()])
    submit = SubmitField(_l('Hinzufügen'))

class OpenGsSystemForm(FlaskForm):
    name = StringField(_l('Name / Bezeichnung'), validators=[DataRequired()])
    description = TextAreaField(_l('Beschreibung'), validators=[DataRequired()])
    number = IntegerField(_l('Anzahl'), validators=[DataRequired()])
    dom_id = HiddenField("", validators=[DataRequired()])
    submit = SubmitField(_l('Hinzufügen'))

class OpenGsCatalogueForm(FlaskForm):
    name = StringField(_l('Name / Bezeichnung'), validators=[DataRequired(), Length(max=128)])
    submit = SubmitField('Katalog hinzufügen')

class OpenGsThreatForm(FlaskForm):
    name = StringField(_l('Name / Bezeichnung'), validators=[DataRequired(), Length(max=128)])
    submit = SubmitField('Gefährdung hinzufügen')

class OpenGsBuildingBlockGroupForm(FlaskForm):
    catalogue_id = SelectField('Katalog', coerce=int, validators=[DataRequired()])
    shorthand = StringField(_l('Kürzel'), validators=[DataRequired(), Length(max=4)])
    name = StringField(_l('Name / Bezeichnung'), validators=[DataRequired(), Length(max=128)])
    description = TextAreaField(_l('Beschreibung (max. 128 Zeichen)'), validators=[Length(min=0,max=128)])
    submit = SubmitField('Bausteingruppe hinzufügen')

class OpenGsBuildingBlockForm(FlaskForm):
    buildingblockgroup_id = SelectField('Bausteingruppe', coerce=int, validators=[DataRequired()])
    prio = SelectField('Umsetzungspriorität', choices=[("","Bitte wählen"),("R1","R1 - Prio 1"),("R2","R2 - Prio 2"),("R3","R3 - Prio 3")], validators=[InputRequired()])
    order = StringField(_l('Ordnungsnummer'), validators=[DataRequired(), Length(max=10)])
    name = StringField(_l('Name / Bezeichnung'), validators=[DataRequired(), Length(max=128)])
    description = TextAreaField(_l('Beschreibung (max. 128 Zeichen)'), validators=[Length(min=0,max=128)])
    submit = SubmitField('Baustein hinzufügen')

class OpenGsRequirementForm(FlaskForm):
    buildingblock_id = SelectField('Baustein', coerce=int, validators=[DataRequired()])
    order = StringField(_l('Ordnungsnummer'), validators=[DataRequired(), Length(max=10)])
    name = StringField(_l('Name / Bezeichnung'), validators=[DataRequired(), Length(max=128)])
    description = TextAreaField(_l('Beschreibung (max. 128 Zeichen)'), validators=[Length(min=0,max=128)])
    protection_level = SelectField('Anforderungsniveau', choices=[("","Bitte wählen"),("BASE","Basis"),("STANDARD","Standard"),("HIGH","Hoch")], validators=[InputRequired()])
    submit = SubmitField('Anforderung hinzufügen')

class OpenGsProcAppRelationForm(FlaskForm):
    coreprocess_id = HiddenField("", validators=[DataRequired()])
    application_id = SelectField('Anwendung', coerce=int, validators=[DataRequired()])
    relation_type = StringField(_l('Kommentar'), validators=[Length(max=50)])
    submit = SubmitField('Hinzufügen')

class OpenGsAppSysRelationForm(FlaskForm):
    application_id = HiddenField("", validators=[DataRequired()])
    system_id = SelectField('System', coerce=int, validators=[DataRequired()])
    relation_type = StringField(_l('Kommentar'), validators=[Length(max=50)])
    submit_appsys = SubmitField('Hinzufügen')

class OpenGsSysNetRelationForm(FlaskForm):
    system_id = HiddenField("", validators=[DataRequired()])
    network_id = SelectField('Netzwerk', coerce=int, validators=[DataRequired()])
    relation_type = StringField(_l('Kommentar'), validators=[Length(max=50)])
    submit_sysnet = SubmitField('Hinzufügen')

class OpenGsActionForm(FlaskForm):
    pass

class DeleteForm(FlaskForm):
    next = HiddenField()

class GsModelDomPreselectForm(FlaskForm):
    dom_id = HiddenField("", validators=[DataRequired()])
    bb_id = HiddenField("", validators=[DataRequired()])
    implementation_decision = SelectField('', validators=[DataRequired()])

class GsModelSysQuickselectForm(FlaskForm):
    dom_id = HiddenField("", validators=[DataRequired()])
    system_id = HiddenField("", validators=[DataRequired()])
    buildingblock_id = SelectField("", validators=[DataRequired()])
    implementation_decision = SelectField('', validators=[DataRequired()])
    submit_sysq = SubmitField('Verknüpfen')

class GsModelAppQuickselectForm(FlaskForm):
    dom_id = HiddenField("", validators=[DataRequired()])
    application_id = HiddenField("", validators=[DataRequired()])
    buildingblock_id = SelectField("", validators=[DataRequired()])
    implementation_decision = SelectField('', validators=[DataRequired()])
    submit_appq = SubmitField('Verknüpfen')