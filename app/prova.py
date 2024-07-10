

#Funzione usata da Fetch per riprendere le vecchie sessioni (da testare)
@app.route("/get_sessions")
def get_sessions():
    try:
        sessions = Session.query.filter(Session.result.isnot(None)).all()
        sessions_list = serialize_list(sessions)
    except Exception as e:
        app.logger.error(f"Error in get_sessions(): {e}")
        sessions_list = []
    
    return jsonify({"sessions": sessions_list})

@app.route("/home",methods=["GET","POST"])
def search_user():
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
        return redirect("/user")

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

            # Create new session
            new_session = Session(user_id=code)
            db.session.add(new_session)

            db.session.commit()
            app.logger.info("Created new user.")
        except Exception as e:
            app.logger.error(f"Error in form(): {e}")
            return redirect("/form")

        # Initialize session code
        session["code"] = code
        return redirect("/user")

    return render_template("form.html", form=form)

@app.route("/user",methods=["GET","POST"])
def info():
    code = session.get("code")
    if code:
        session_data_db.update({"code":code})
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
        print(session_data_db)
        return render_template("info.html", row=row, year=date.today())
    else:
        return redirect("/")
    
@app.route("/user/workout",methods=["GET","POST"])
def user_session():
    code = session.get("code")
    if code:
        workouts = {}
        n_trainings = Training.query.count()
        
        # Get all the trainings
        for n in range(1, n_trainings + 1):
            names = []  # List of exercises" names
            training = Training.query.get(n)  # Training
            exercises = TrainingExercise.query.filter_by(training_id=training.id).all()  # Exercises in training
            for ex in exercises:
                exercise = Exercise.query.get(ex.exercise_id)
                if exercise:
                    names.append(exercise.name)
            workouts[training.name] = names
        
        n_session = Session.query.filter_by(user_id=code).order_by(Session.number.desc()).first()
        if n_session:
            n_session = n_session.number
        else:
            n_session = 0

        app.logger.info("Accessed DB")
        
        if request.method == "POST":
            exercises_list = serialize_list(get_exercises(request.form.get("workout")))
            session_data_db.update({"exercises_list":exercises_list} )
            return redirect(url_for("choose_vr"))
        
        return render_template("choose_workout.html", workouts=workouts, n_session=n_session)
    else:
        return redirect("/")
    

@app.route('/user/create_workout',methods=['GET','POST'])
def new_training():
    if 'code' in session:
        exs = New_Workout()
        if exs.validate_on_submit():
            exercises = []
            for i in range(1, 6):  # Assuming you have 5 exercises
                exercise_id = request.form.get(f'ex{i}')
                exercise = Exercise.query.get(exercise_id)
                if exercise:
                    exercises.append(exercise.serialize())
            session_data_db.update({"exercises_list":exercises} )
            return redirect(url_for('choose_vr'))
        else:
            return render_template("new_workout.html",form=exs)
    else:
        return render_template(url_for('search_user'))

@app.route("/user/session/choose_vr",methods=["GET","POST"])
def choose_vr():
    code = session.get("code")
    print(session_data_db["exercises_list"])
    if code:
        if request.method == "POST":
            ip = request.form.get("client")
            msg = json.dumps(session_data_db['exercises_list'])
            msg = 'DATA:'+msg
            if send_to_client(msg,client_ips[int(ip)]):
                return redirect(url_for("session_start"))
            else:
                return '[ERRORE] non è riuscita la connessione con il visore'
        return render_template("choose_vr.html",clients_ip = client_ips)
    else:
        return redirect("/")
    

@app.route("/user/session")
def session_start():
    code = session["code"]
    if code:
        #user info
        user = User.query.filter_by(code = code).first()
        return render_template('session.html',user = user,data = session_data_db["exercises_list"])
    else:
        return redirect("/")