from app import app
from flask import request,redirect,url_for,flash,session,render_template,jsonify,send_file
import re
from datetime import date,datetime
from app.models import db,User,Session,Training,Exercise,TrainingExercise,UserExerciseInfo
from sqlalchemy import func
from app.form import Registration,New_Workout
from app.utils import serialize_list,get_exercises
from app.socket_udp import get_clients,send_connect,is_connected,save_data,send_data,get_data
import csv
import io

@app.route("/")
def welcome():
    return render_template("welcome.html")

@app.route("/connect-vr",methods=["GET","POST"])
def connection():
    if request.method == "POST":
        ip = int(request.form.get("client"))
        #SEND CONNECT MESSAGE TO CLIENT, SET CONNECTED TO TRUE AND START COMMUNICATION
        try:
            send_connect(get_clients()[ip])
        except Exception as e:
            print(f"Error while connecting: {e}")
        if is_connected():
            return redirect(url_for("search_user"))
        else:
            flash("Errore nella connessione riprovare","error")
            return redirect(request.url)
    return render_template("choose_vr.html",clients_ip = get_clients())

@app.route("/search-user",methods=["GET","POST"])
def search_user():
    if is_connected():
        if request.method == "POST":
            search = request.form.get("codice")
            if not search:
                flash("Inserisci il codice utente.", "error")
                return redirect(request.url)
            
            if not re.match("^[0-9]*$", search):
                flash("Il codice deve essere composto solo da numeri.", "error")
                return redirect(request.url)

            try:
                user = User.query.filter_by(code=search).first()
            except Exception as e:
                app.logger.error(f"Error searching user: {e}")
                flash("Si è verificato un errore nella ricerca dell'utente.", "error")
                return redirect(request.url)

            if not user:
                link = url_for("form")
                flash(f"Il codice inserito non è registrato. Per registrare l\"utente vai al seguente <a href=\"{link}\">LINK</a>", "info")
                return redirect(request.url)

            app.logger.info("User found")
            session["code"] = user.code
            return redirect(url_for("info"))

        return render_template("home.html")
    else:
        flash("Devi connetterti al visore","disconnected")
        return render_template("home.html")

@app.route("/form",methods=["GET","POST"])
def form():
    form = Registration()
    if form.validate_on_submit():
        try:
            # Form values for the registration
            name = request.form.get("name").capitalize()
            surname = request.form.get("surname").capitalize()
            code = request.form.get("code")
            sex = request.form.get("sex")
            dob = datetime.strptime(request.form.get("dob"), "%Y-%m-%d")
            info1 = request.form.get("info1").capitalize()
            info2 = request.form.get("info2").capitalize()

            # Create user object
            new_user = User(name=name, surname=surname, code=code, dob=dob, sex=sex, info1=info1, info2=info2)
            db.session.add(new_user)
            db.session.commit()
            app.logger.info("Created new user.")

        except Exception as e:
            app.logger.error(f"Error in form(): {e}")
            return redirect("/form")

        # Initialize session code
        session["code"] = code
        return redirect(url_for("info"))
    return render_template("form.html", form=form)

@app.route("/user",methods=["GET","POST"])
def info():
    code = session.get("code")
    if code and is_connected():
        # Get user info
        row = User.query.filter_by(code=code).first()
        app.logger.info("Found user's info")
        
        if request.method == "POST":
            try:
                if "form1-submit" in request.form:
                    modifica1 = request.form.get("modifica1").capitalize()
                    row.info1 = modifica1
                elif "form2-submit" in request.form:
                    modifica2 = request.form.get("modifica2").capitalize()
                    row.info2 = modifica2
                db.session.commit()
                app.logger.info("User info modified")
                return redirect(request.url)
            except Exception as e:
                app.logger.error(f"Error in info(): {e}")
                return redirect(request.url)
        return render_template("info.html", row=row, year=date.today())
    else:
        return redirect(url_for("search_user"))


@app.route("/session",methods=["GET","POST"])
def choose_workout():
    code = session.get("code")
    if code and is_connected():

        workouts = {}
        n_trainings = Training.query.count()
        
        # Get all the trainings
        for n in range(1, n_trainings + 1):
            names = []  # List of exercises names
            training = Training.query.get(n)  # Training
            exercises = TrainingExercise.query.filter_by(training_id=training.id).all()  # Exercises in training
            for ex in exercises:
                exercise = Exercise.query.get(ex.exercise_id)
                if exercise:
                    names.append(exercise.name)
            workouts[training.name] = names
        
        sessions = Session.query.filter_by(user_id=code).order_by(Session.number.desc()).all()

        if not sessions:
            n_session = 1
        else:
            highest_session = sessions[0]
            n_session = highest_session.number

            for s in sessions:
                if s.result is None:
                    flash("Unfished session","session_alert")
            n_session += 1

        app.logger.info("Accessed DB")
        
        if request.method == "POST":
            # Handle the POST request
            list_exercises = []
            exercises_list = serialize_list(get_exercises(request.form.get("workout")))
            for ex in exercises_list:
                list_exercises.append(ex["id"])
                new_session = Session(code, n_session, ex["id"])
                db.session.add(new_session)
            db.session.commit()
            save_data(code,n_session,list_exercises)
            return redirect(url_for("confirm_session"))
            
        # Render the template for the GET request
        return render_template("choose_workout.html", workouts=workouts, n_session=n_session,dev=False)
    else:
        flash("Devi connetterti al visore", "disconnected")
        return redirect(request.url)
    

@app.route("/user/create_workout/<n>", methods=["GET", "POST"])
def new_training(n):
    code = session.get("code")
    if code and is_connected():        
        exs = New_Workout()
        list_exercises = []
        if exs.validate_on_submit():
    
            for i in range(1, 6):  # Assuming you have 5 exercises
                exercise_id = request.form.get(f"ex{i}")
                list_exercises.append(int(exercise_id))
                new_session = Session(code, n, exercise_id)
                db.session.add(new_session)

            db.session.commit()
            save_data(code,n,list_exercises)
            return redirect(url_for("confirm_session"))
        else:
            return render_template("new_workout.html", form=exs, n=n)  # Pass n_session to template
    else:
        flash("Devi connetterti al visore", "disconnected")
        return redirect(request.url)
    

@app.route("/restart_session")
def restart_session():
    
    user_id = session.get("code")
    max_number = Session.query.with_entities(func.max(Session.number)).filter_by(user_id=user_id).scalar()
    sessions = Session.query.filter_by(user_id=user_id, number=max_number).all()

    for s in sessions:
        db.session.delete(s)
    db.session.commit()
    return redirect(url_for("choose_workout"))


@app.route("/continue_session")
def continue_session():
    
    user_code = session.get("code")  # Get the user code from the session
    highest_session = Session.query.filter_by(user_id=user_code).filter(Session.result.is_(None)).order_by(Session.number.desc()).first()
    
    if highest_session:
        # Get the session number
        n = highest_session.number
        
        # Find all exercises with the same session number
        exercises = Session.query.filter_by(user_id=user_code, number=n).filter(Session.result.is_(None)).all()
        list_exercises = []
        for ex in exercises:
            list_exercises.append(ex.exercise)
        save_data(user_code,n,list_exercises)
        return redirect(url_for("confirm_session"))
    else:
        return "No session found", 404

@app.route("/user/session")
def session_start():
    saved_data = get_data()
    code = session["code"]
    if code and is_connected():
        e = send_data()
        if e:
            list_exercises = []
            sessions = Session.query.filter_by(user_id=code).order_by(Session.number.desc()).first()
            if sessions is not None:
                info = {} 
                # Recupera tutte le sessioni con lo stesso numero
                exercises_in_session = Session.query.filter_by(number=sessions.number, user_id=code).all()
                # Aggiungi ogni esercizio alla lista
                for ex in exercises_in_session:
                    i = UserExerciseInfo.query.filter_by(user_id=code, exercise_id=ex.exercise).first()
                    if i:
                        info[ex.exercise] = i.info
                    exercise = Exercise.query.filter_by(id=ex.exercise).first()
                    if exercise:
                        list_exercises.append(exercise)
            user = User.query.filter_by(code=saved_data.get("id",[])).first()
            return render_template("session.html",user = user,data=list_exercises,info=info,requested_ex=saved_data.get("list_exercises",[]))
        else:
            return render_template("session_error.html")
    else:
        flash("Devi connetterti al visore", "disconnected")
        return redirect(request.url)
    
@app.route("/user/confirm_session")
def confirm_session():
    saved_data = get_data()
    code = session["code"]
    if code and is_connected():
        list_exercises = []
        sessions = Session.query.filter_by(user_id=code).order_by(Session.number.desc()).first()
        if sessions is not None:
            # Recupera tutte le sessioni con lo stesso numero
            exercises_in_session = Session.query.filter_by(number=sessions.number, user_id=code).all()
            # Aggiungi ogni esercizio alla lista
            for ex in exercises_in_session:
                exercise = Exercise.query.filter_by(id=ex.exercise).first()
                if exercise:
                    list_exercises.append(exercise)
        user = User.query.filter_by(code=saved_data["id"]).first()
        return render_template("confirm_session.html",user = user,session = sessions.number,data=list_exercises,requested_ex=saved_data["list_exercises"])
    else:
        flash("Devi connetterti al visore", "disconnected")
        return redirect(request.url)

@app.route('/register_ex', methods=['POST'])
def handle_update():
    ex_id = request.form.get('ex_id')
    user_id = request.form.get('user_id')
    user_session = request.form.get('user_session')

    try:
        session = Session.query.filter_by(user_id=user_id, number=user_session, exercise=ex_id).first()
        if session is None:
            return jsonify({"status": "error", "message": "Session not found"}), 404
        
        session.result = b"NON REGISTRATO"
        get_data().get("list_exercises").remove(int(ex_id))
        db.session.commit()
        return jsonify({"status": "success", "message": "Exercise updated successfully."}), 200
    
    except Exception as e:
        print(f"Errore nel modificare l'esercizio: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500  # Internal server error

@app.route("/save_session",methods=["POST"])
def save():
    form_data = request.form
    user_code = form_data.get("user_id")
    exercise_results = {key: value for key, value in form_data.items() if key.startswith('ex')}
    for key, val in exercise_results.items():
        ex = int(key.split("_")[1])
        s = Session.query.filter_by(user_id=user_code).order_by(Session.number.desc()).first().number
        session = Session.query.filter_by(user_id = user_code,number = s,exercise = ex).first()
        session.info = val
        res = UserExerciseInfo(user_code,ex,val)
        db.session.merge(res)
        db.session.commit()
    return render_template("session_complete.html")


@app.route("/get_sessions")
def get_sessions():
    if session.get("code"):
        s = Session.query.filter_by(user_id=session.get("code")).filter(Session.result.isnot(None)).order_by(Session.number.desc()).first()
        out = []
        if s:
            for x in range(1,s.number+1):
                out.append((x, s.user_id))
        return jsonify({"list": out})


@app.route('/download_csv')
def download_csv():

    output = io.StringIO()
    writer = csv.writer(output)
    code = session["code"]

    writer.writerow(['Nome', 'Cognome', 'ID', 'Sessione', 'Esercizio','Peso/Resistenza', 'Risultato'])

    sessions = Session.query.filter_by(user_id=code).all()

    if not sessions:
        return "No sessions found", 404

    data = io.StringIO()
    writer = csv.writer(data)
    
    # Write headers if needed
    writer.writerow(['Nome', 'Cognome', 'ID', 'Sessione', 'Esercizio','Peso/Resistenza', 'Risultato'])

    for s in sessions:
        
        exercise = Exercise.query.filter_by(id=s.exercise).first()
        user = User.query.filter_by(code=code).first()

        if exercise and user:
            exercise_name = exercise.name
            user_name = user.name
            user_surname = user.surname
            result = s.result.decode() if s.result else "No result"
            peso = s.info if s.result else "No info"
            writer.writerow([user_name, user_surname, code, s.number, exercise_name, peso, result])

    output.seek(0)

    return send_file(
        io.BytesIO(data.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'{code}_STORICO.csv'
    )

@app.route('/download_csv/<n>')
def create_csv(n):
    parts = n.split('_')
    user_id = parts[0]
    session_number = parts[1]

    try:
        session_number = int(session_number)
    except ValueError:
        return "Invalid session number", 400

    sessions = Session.query.filter_by(user_id=user_id, number=session_number).all()

    if not sessions:
        return "No sessions found", 404

    data = io.StringIO()
    writer = csv.writer(data)
    
    # Write headers if needed
    writer.writerow(['Nome', 'Cognome', 'ID', 'Sessione', 'Esercizio','Peso/Resistenza', 'Risultato'])

    for s in sessions:
        
        exercise = Exercise.query.filter_by(id=s.exercise).first()
        user = User.query.filter_by(code=user_id).first()

        if exercise and user:
            exercise_name = exercise.name
            user_name = user.name
            user_surname = user.surname
            result = s.result.decode() if s.result else "No result"
            peso = s.info if s.result else "No info"
            writer.writerow([user_name, user_surname, user_id, session_number, exercise_name, peso, result])

    data.seek(0)

    return send_file(
        io.BytesIO(data.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'{user_id}_{session_number}.csv'
    )