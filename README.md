# Meow for E-Kittens

Press a hotkey and 3 to 6 kittens pop onto the stream for 3 seconds, then disappear. The page background stays transparent, so only the kittens are visible. Nothing is drawn on your desktop.

## Install

Quit OBS, then run:

```bash
python3 install.py
```

That adds the overlay to the current scene collection, places it over the canvas, binds **F8**, and opens OBS. The kittens play once as OBS loads, then again each time you press F8. To pick another key: `python3 install.py --key K`.

You need an OBS build that includes the Browser source. The Flathub build and the build from [obsproject.com](https://obsproject.com/download) include it. The `obs-studio` package in Ubuntu’s default repos often does not.

## Add it by hand

1. In the scene you stream, add a **Browser** source.
2. Check **Local file** and choose `overlay.html` from this folder.
3. Set **Width** and **Height** to your base canvas resolution (Settings → Video). Check **Use custom frame rate** and set FPS to **60**.
4. Leave the default Custom CSS in place so the background stays transparent.
5. Leave **Shutdown source when not visible** and **Refresh browser when scene becomes active** unchecked. The page stays blank until the hotkey.
6. Leave the eye icon on, and move the source above the game in the Sources list. Select the source and use **Edit → Transform → Fit to screen** so it covers the canvas.
7. Open **Tools → Scripts**, press **+**, and add `meow-for-e-kittens.lua`. If the source is missing from the list, add the Browser source first, then press **Reload source list**.
8. Select that Browser source in the script.
9. Open **Settings → Hotkeys**, find **Meow for E-Kittens**, and bind a key or mouse button.

**Play kitten burst** in the script window fires it without the hotkey. Pressing the hotkey during a burst starts a new one.

Opening `overlay.html` in a normal browser plays one burst on a checkerboard so you can see the transparency. OBS does not play that preview burst; it waits for the hotkey.

## If nothing appears

- The Browser source eye icon is on, and the source is above the game on the scene you are actually streaming.
- The script log (**Tools → Scripts → Script Log**) says which source it triggered.
- Custom CSS was not replaced with a solid background.
- Studio mode is fine: the hotkey updates the browser source itself, including the program output, as long as that source is on the live scene.
