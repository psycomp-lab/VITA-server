from flask_wtf import FlaskForm
from wtforms import validators,StringField,SelectField,DateField,TextAreaField, RadioField
from .models import User
#############   REGISTRATION'S FORM   ###############


def check_user(form, field):
    user = User.query.filter_by(code=field.data).first()
    if user:
        raise validators.ValidationError('Esiste già un utente con questo codice.')

class Registration(FlaskForm):

    name = StringField(u'Nome',validators=[validators.InputRequired(message='Devi inserire il nome!')])
    surname = StringField(u'Cognome',validators=[validators.InputRequired(message='Devi inserire il cognome!')])
    code = StringField(u'Codice',validators=[validators.input_required(message='Devi inserire il codice!'),validators.Regexp(regex='^[0-9]*$',message='Il codice può contenere solo numeri'),validators.Length(max=10,message='Il codice deve essere lungo tot caratteri'),check_user])
    sex = SelectField(u'Sesso',choices=[('M','Maschio'),('F','Femmina'),('O','Altro')],validate_choice=True)
    # controllo anno?
    dob = DateField(u'Data di nascita',validators=[validators.InputRequired(message='Inserisci una data')],format='%Y-%m-%d')
    info1 = TextAreaField(u'Condizioni fisiche',default='',validators=[validators.Length(max=250,message='Il campo deve avere dai 5 ai 250 caratteri')])
    info2 = TextAreaField(u'Condizioni di salute',default='',validators=[validators.Length(max=250,message='Il campo deve avere dai 5 ai 250 caratteri')])

class New_Workout(FlaskForm):

    ex1 = RadioField("Primo esercizio",validators=[validators.InputRequired(message="Devi scegliere un esercizio")],choices=[("1","Chair standing (squat)"),("6","Static lunge")])
    ex2 = RadioField("Secondo esercizio",validators=[validators.InputRequired(message="Devi scegliere un esercizio")],choices=[("2","Push up"),("7","Row elastic band")])
    ex3 = RadioField("Terzo esercizio",validators=[validators.InputRequired(message="Devi scegliere un esercizio")],choices=[("3","Seated bicep curl"),("8","Tricep extension resistance band")])
    ex4 = RadioField("Quarto esercizio",validators=[validators.InputRequired(message="Devi scegliere un esercizio")],choices=[("4","Seated lateral shoulder raieses"),("9","Chair calf raise")])
    ex5 = RadioField("Quinto esercizio",validators=[validators.InputRequired(message="Devi scegliere un esercizio")],choices=[("5","Slanci posteriori in piedi"),("10","Crunch/Seated crunch")])

