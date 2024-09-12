document.addEventListener("DOMContentLoaded", function() {

    var socket = io.connect('http://' + document.domain + ':' + location.port);

    socket.on('connect', function() {
        console.log('Connected to server...');
    });

    socket.on("disconnect-vr",function(){
        console.log("socket disconnected");
        alert("Il visore è stato disconnesso.");
        window.location.href = "/connect-vr"; 
    })

    socket.on("exercise", function(id) {
        console.log("Finished exercise: " + id);
        document.getElementById(id).setAttribute('class', 'mx-4 fa-xl fa-solid fa-check');
    });

    socket.on("end_session", function() {
        console.log("Session ended");
        var button = document.getElementById("next");
        button.classList.remove("btn-outline-primary");
        button.classList.add("btn-primary");
        button.disabled = false;
    });


    const pause = document.getElementById("pause");

    const play = document.getElementById("play");
    
    if(pause !== null && play !== null){
        pause.addEventListener("click", () => {
            pause.disabled = true;
            play.disabled = false;
            document.getElementById("testo_pausa").classList.remove("d-none");
            socket.emit("pause");
        });
        play.addEventListener("click", () => {
            play.disabled = true;
            pause.disabled = false;
            document.getElementById("testo_pausa").classList.add("d-none");
            socket.emit("restart");
        })
    }
    


});