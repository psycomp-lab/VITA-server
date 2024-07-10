from app.models import TrainingExercise,Exercise,User,Session,db

def serialize_list(objects:list):
    serialized_list = []
    for obj in objects:
        serialized_list.append(obj.serialize())  # Assuming you have a serialize method in your SQLAlchemy models
    return serialized_list


def get_exercises(workout):
    training_ex = TrainingExercise.query.filter_by(training_id=workout)
    exercises = []
    for ex in range(training_ex.count()):
        exercises.append(Exercise.query.filter_by(id=training_ex.all()[ex].exercise_id).first())
    return exercises

def create_file_session(code:str,n_session:int,data):
    user_info = f'Codice : {code};\nNome : {User.query.filter_by(code=code).first().name};\nCognome : {User.query.filter_by(code=code).first().surname};\nSessione : {n_session};\n'
    exercises = "Esercizi : "
    for el in data:
        exercises+=f' {el["name"]} /'
    exercises = exercises[:-1]
    row = Session.query.filter_by(user_id=code).first()
    row.result = (user_info+exercises).encode()
    db.session.commit()