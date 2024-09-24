from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey, Column, Integer, String, Date, LargeBinary
from sqlalchemy.orm import relationship

db = SQLAlchemy()

############################       DATABASE       ################################

class Session(db.Model):
    __tablename__ = 'users_session'
    user_id = Column('user_id',String,ForeignKey('users.code'),primary_key=True)
    number = Column(Integer,primary_key=True,default=1)
    exercise = Column(Integer, ForeignKey('exercises.id'), primary_key=True)
    result = Column(LargeBinary,nullable=True)
    info = Column(String,nullable=True)
    def __init__(self,user_id:int,number:int,exercise:int) -> None:
        self.user_id = user_id
        self.number = number
        self.exercise = exercise
        self.result = None
        self.info = None



    def __repr__(self) -> str:
        return f'Sessione Nº {self.number}'
    
    def serialize(self):
        if self.result:
            result_text = self.result
        else:
            result_text = None
        
        return {
            'user': self.user_id,
            'number': self.number,
            'result': result_text
        }
    
class User(db.Model):   
    __tablename__ = 'users'
    id = Column(Integer, primary_key = True)
    name = Column(String(20))
    surname = Column(String(20))
    code = Column(String(20), unique = True)
    dob = Column(Date)
    sex = Column(String(1))
    info1 = Column(String(250),default = "")
    info2 = Column(String(250),default = "")

    def __init__(self,name:str,surname:str,code:str,dob,sex:str,info1:str,info2:str) -> None:
        self.name = name
        self.surname = surname
        self.code = code
        self.sex = sex
        self.dob = dob
        self.info1 = info1
        self.info2 = info2
        
    def __repr__(self) -> str:
        return f'Nome: {self.name}  Cognome: {self.surname}  Codice: {self.code}'
    
class TrainingExercise(db.Model):
    __tablename__ = 'training_exercise'
    training_id = Column('training_id',Integer,ForeignKey('trainings.id'),primary_key=True)
    exercise_id = Column('exercise_id',Integer,ForeignKey('exercises.id'),primary_key=True)

class Training(db.Model):
    __tablename__ = 'trainings'
    id = Column(Integer,primary_key=True)
    name = Column(String(20))
    exercises = relationship('Exercise',secondary='training_exercise',back_populates='trainings')

class Exercise(db.Model):
    __tablename__ = 'exercises'
    id = Column(Integer,primary_key=True)
    name = Column(String(20))
    trainings = relationship('Training',secondary='training_exercise',back_populates='exercises')
    #da aggiungere a tutti quelli da passare al visore
    def serialize(self):
        return {
            'id' : self.id ,
            'name' : self.name
        }
    
class UserExerciseInfo(db.Model):
    __tablename__ = 'info'
    user_id = Column('user_id',String,ForeignKey('users.id'),primary_key=True)
    exercise_id = Column(Integer, ForeignKey('exercises.id'), primary_key=True)
    info = Column(String)

    def __init__(self,user_id:int,exercise_id:int,info:str) -> None:
        self.user_id = user_id
        self.exercise_id = exercise_id
        self.info = info
