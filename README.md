# PyEdit4
Python Editor written in python Gtk3

### Requirements

- Gtk3 (Gtk, Gdk, GLib, GtkSource, GObject, Vte, GdkPixbuf)
- python3 >= 3.6
- [pyflakes](https://pypi.org/project/pyflakes/) and [zenity](https://help.gnome.org/users/zenity/stable/) (for code check)
- devhelp (for help)

### Usage

```
git clone https://github.com/Axel-Erfurt/PyEdit4.git
cd PyEdit4
python3 ./PyEdit4.py
```

![alt](https://raw.githubusercontent.com/Axel-Erfurt/PyEdit4/main/screenshot.png)

You can add Code Snippets as .txt files in the _templates_ folder

### Shortcuts

- Ctrl+O -> open file
- Ctrl+S -> save file
- Ctrl+N -> new file
- Ctrl+F -> find

- F1 ->  show help for selected, needs devhelp
- F2 ->  toggle comment on line (or on multiple lines)
- F3 ->  set selected text in (round) brackets
- F4 ->  set selected text in double quotes
- F5 ->  run Script
- F6 ->  set selected text in double quotes inside (round) brackets
- F7 unindent selected lines
- F8 indent selected lines
- F9 -> find previous (selected)
- F10 -> find next (selected)
