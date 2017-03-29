module.exports = function (io) {
    var express = require('express');
    var router = express.Router();

    router.get('/', function (req, res, next) {
        res.redirect(301, 'http://udg.mx');
    });
  /* GET home page. */
    router.get('/:id([a-zA-Z0-9_.-]{36})', function(req, res, next) {
        console.log('Server');
        res.send('Chat Server.');
        io.sockets.on('connection', function(socket) {
            console.log('A user connected');

            socket.on('room', function (room) {
                console.log(room);
                socket.join(room);
                io.sockets.in(room).emit('message', 'Joined');
                setTimeout(function(){
                    io.sockets.in(room).emit('message', 'Puto');
                }, 4000);
                setTimeout(function(){
                    io.sockets.in(room).emit('message', 'Joto');
                }, 8000);
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
