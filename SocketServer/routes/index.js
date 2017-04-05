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
                    io.sockets.in(room).emit('message', '{"lat": 100.000000, "lng": 100.000001}');
                }, 8000);
            });

            socket.on('disconnect', function () {
                console.log('A user disconnected');
            });

            socket.on('message', function (msg) {
                io.sockets.in(io.sockets.rooms[socket.id]).emit('message', msg);
            });
        });
    });
    return router
};
