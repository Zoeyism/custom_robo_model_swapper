# The Custom Robo Model Swapper
Model swapper for Custom Robo for the Gamecube!

This is an app designed to allow people to give different characters different models in Custom Robo for the GameCube. 
It includes an easy to use front-end that creates the modified files, which the user then manually puts into their ROM. 

There are limitations to the app, but the biggest ones are:
  1. No way to convert Custom Robo models to modern formats, or to patch in modern models; the game uses a properietary 
     model format in BIN files that I've only managed to partially document, and I don't have experience in converting model formats, so
     this isn't likely to change.
  2. The model being overwritten has to have an equal or smaller file size than the replacement model. There are some potential ways to
     get around this, but none that I've implemented or tested yet.
  3. There is no patcher for the ROM, so the user has to manually replace the files in the ROM.
  
Workarounds and changes that would resolve these issues may come in the future, but I haven't started working on either and
can't guarantee that they will even happen at all.

Usage instructions:
  1. Download the release, and extract from the ZIP file.
  2. Run the .exe in the folder. 
  3. Select which models you want to be replaced on the left side, and
     which models you want to replace them with on the right.
  4. When you're ready, click "Swap Models".
     If any of the models can't be replaced due to file size issues, an error will pop up and let you know.
  5. If the models swap successfully, you will find the files in the "result_files" folder, named "rpg_f_models.BIN"
     and "rpg_t_models.BIN".
  6. Open your Custom Robo ROM using Dolphin or Gamecube Rebuilder, and navigate to the "scenario_us" folder inside.
  7. Replace the two files inside that folder that have the same names as the app-created files. Save your changes.
  8. You're done! All gameplay and in-game cutscenes will have that character replaced with your selected model.
  
Let me know about any issues or bugs that come up!
Thanks to the developer of PySimpleGUI for making it easy to make this app!
