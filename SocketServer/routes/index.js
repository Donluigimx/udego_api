module.exports = function (io) {
    var express = require('express');
    var router = express.Router();

  /* GET home page. */
    router.get('/:id([a-zA-Z0-9_.-]{64})', function(req, res, next) {
        room = req.params.id;
        res.send('Chat Server.');
        io.on('connection', function(socket){
            console.log('A user connected');

            socket.on('room', function (room) {
                console.log(room);
                socket.join(room);
            });
            //Send a message after a timeout of 4seconds
            setTimeout(function(){
                io.sockets.in('0saA_1.-_asdw-ojisdk').send('Si jala');
            }, 4000);
            socket.on('disconnect', function () {
                console.log('A user disconnected');
            });
        });
    });
    return router
};
