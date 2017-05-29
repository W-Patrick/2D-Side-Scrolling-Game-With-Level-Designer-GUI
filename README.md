# 2D-Side-Scrolling-Game-With-Level-Designer-GUI
The foundation of a two dimmensional side scrolling game with a GUI that allows you to design levels for it.

The script called game.py is the main game. When running the main game you must pass in the name of the level that you want to load
as a command line argument. This level must be located in the 'levels' file and you do not need to include the 'stg' file extension
when passing in the file name. This game is being built using the popular pygame library.

How to play:
  * Press 'A' to shoot
  * Press the spacebar to jump
  * Press the arrow keys to move
  * If you want enemies to exist in the level, go to the 'Rules' class
    in game.py and change spawn_count to any number greater than zero
