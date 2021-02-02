#!/usr/bin/python3
# -*- coding: utf-8 -*-

### created in January 2021 by Axel Schneider
### https://github.com/Axel-Erfurt/
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version('Keybinder', '3.0')
gi.require_version('GtkSource', '3.0')
gi.require_version('Vte', '2.91')
from gi.repository import Gtk, Gdk, GLib, GtkSource, GObject, Vte, GdkPixbuf
import sys
from subprocess import run, Popen
from os import path, environ, listdir
from urllib.request import url2pathname
import warnings
from shutil import copyfile, which

dnd_list = [Gtk.TargetEntry.new("text/uri-list", 0, 80)]

warnings.filterwarnings("ignore")
import configparser

# terminal class
class Terminal(Vte.Terminal):
    """Defines a simple terminal"""
    def __init__(self):
        super(Vte.Terminal, self).__init__()

        self.spawn_async(Vte.PtyFlags.DEFAULT, 
            environ["HOME"],
            ["/bin/sh"],
            None,
            GLib.SpawnFlags.DO_NOT_REAP_CHILD,
            None,
            None,
            -1,
            None,
            None
            )
        self.set_rewrap_on_resize(True)
        self.set_font_scale(0.9)
        self.set_scroll_on_output(True)
        self.set_scroll_on_keystroke(True)
        palette = None
        self.set_colors(Gdk.RGBA(0.8, 0.8, 0.8, 1.0), Gdk.RGBA(0.3, 0.3, 0.3, 1.0), palette)
        self.connect("key_press_event", self.copy_or_paste)

        self.set_scrollback_lines(-1)
        self.set_audible_bell(0)

    def copy_or_paste(self, widget, event):
        control_key = Gdk.ModifierType.CONTROL_MASK
        shift_key = Gdk.ModifierType.SHIFT_MASK
        if event.type == Gdk.EventType.KEY_PRESS:
            if event.state == shift_key | control_key:
                if event.keyval == 67:
                    self.copy_clipboard()
                elif event.keyval == 86:
                    self.paste_clipboard()
                return True


class MyWindow(Gtk.Window):
    def __init__(self, parent=None):
        super(MyWindow, self).__init__()

    def main(self, argv):
        
        self.config = configparser.ConfigParser()
        self.config.read('config.conf')
        if not self.config.has_section("window"):
            self.config.add_section("window")
        if not self.config.has_section("files"):
            self.config.add_section("lastfiles")
        self.lastfiles = []
        self.new_text = "#!/usr/bin/python3\n# -*- coding: utf-8 -*-\n\n"
        self.current_file = ""
        self.current_filename = ""
        self.current_folder = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOCUMENTS) ###path.expanduser("~")
        self.is_changed = False
        
        # check devhelp exists
        if not (which("devhelp")) == "":
            self.can_devhelp = True
            print("devhelp available")
        else:
            self.can_devhelp = False
            print("devhelp not available")
        
        builder = Gtk.Builder()
        GObject.type_register(GtkSource.View)
        builder.add_from_file("ui.glade")

        screen = Gdk.Screen.get_default()    
        self.screenwidth = screen.get_width ()
        css_provider = Gtk.CssProvider()
        css_provider.load_from_path('ui.css')

        context = Gtk.StyleContext()
        context.add_provider_for_screen(screen, css_provider,
          Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
          
        self.win = builder.get_object("window")
        
        self.q_icon = builder.get_object("question_icon")
        self.about_icon = builder.get_object("about_icon")
        
        # headerbar buttons
        self.btn_save = builder.get_object("btn_save")
        self.btn_save.connect('clicked', self.save_file)
        self.btn_save.set_relief(Gtk.ReliefStyle.NONE)
        
        self.btn_save_as = builder.get_object("btn_save_as")
        self.btn_save_as.connect('clicked', self.on_save_file)
        self.btn_save_as.set_relief(Gtk.ReliefStyle.NONE)

        self.btn_new = builder.get_object("btn_new")
        self.btn_new.connect('clicked', self.on_new_file)
        self.btn_new.set_relief(Gtk.ReliefStyle.NONE)
        
        self.btn_open = builder.get_object("btn_open")
        self.btn_open.connect('clicked', self.on_open)
        self.btn_open.set_relief(Gtk.ReliefStyle.NONE)
        
        # recent files 
        self.btn_up = builder.get_object("btn_up")
        self.btn_menu = Gtk.MenuButton(label="recent Files ...")
        self.btn_menu.set_image_position(1)
        self.btn_menu.set_image(self.btn_up)
        self.btn_menu.set_relief(Gtk.ReliefStyle.NONE)
        self.btn_menu.set_name("menubutton")       
        self.recent_menu = Gtk.Menu()
        self.btn_menu.set_popup(self.recent_menu)
        
        self.btn_box = builder.get_object("btn_box")
        self.btn_box.pack_start(self.btn_menu, False, False, 1)
        self.btn_box.reorder_child(self.btn_menu, 0)

        
        # run code
        self.btn_run = builder.get_object("btn_run")
        self.btn_run.connect('clicked', self.on_run)
        self.btn_run.set_relief(Gtk.ReliefStyle.NONE)
        
        self.btn_fm = builder.get_object("btn_filemanager")
        self.btn_fm.connect('clicked', self.on_fm)
        self.btn_fm.set_relief(Gtk.ReliefStyle.NONE)
        
        # check_code
        self.btn_check_code = builder.get_object("btn_check_code")
        self.btn_check_code.connect('clicked', self.on_check_code)
        self.btn_check_code.set_relief(Gtk.ReliefStyle.NONE)
        
        # color button
        self.btn_color = builder.get_object("btn_color")
        self.btn_color.connect('clicked', self.on_get_color)
        self.btn_color.set_relief(Gtk.ReliefStyle.NONE)        
        
        # entry go to line
        self.entry_goto = builder.get_object("entry_goto")
        self.entry_goto.connect("activate", self.on_goto_line)
        
        # sourceview
        self.editor = builder.get_object("editor")
        self.editor.drag_dest_set_target_list(dnd_list)
        self.editor.connect("drag_data_received", self.on_drag_data_received)        
        self.editor.connect("key_press_event", self.editor_key_press)
        self.editor.set_smart_backspace(True)
        self.editor.set_show_line_marks(True)
                
        # buffer
        self.buffer = GtkSource.Buffer()
        self.buffer.set_text(self.new_text)
        self.editor.set_buffer(self.buffer)
        self.buffer.connect('changed', self.is_modified)
        
        # code language
        self.lang_manager = GtkSource.LanguageManager()
        self.buffer.set_language(self.lang_manager.get_language("python"))
        
        # completion
        self.text_completion = self.editor.get_completion()
        self.view_provider = GtkSource.CompletionWords.new('main')
        self.view_provider.register(self.buffer)
        self.text_completion.add_provider(self.view_provider) 
        
        keyword_provider = GtkSource.CompletionWords.new('keywords')
        keyword_provider.props.minimum_word_size = 2
        keyword_buffer = GtkSource.Buffer()
        # load words from file
        keywords = open("wordlist.txt", 'r').read()
        keyword_buffer.set_text(keywords)
        keyword_provider.register(keyword_buffer)
        self.text_completion.add_provider(keyword_provider) 
        
        # Settings for SourceView Find
        self.searchbar = builder.get_object("searchbar")
        self.searchbar.connect("key_press_event", self.searchbar_key_press)
        self.search_settings = GtkSource.SearchSettings()
        self.search_settings.set_search_text("initial highlight")
        self.search_settings.set_wrap_around(True)
        self.search_context = GtkSource.SearchContext.new(self.buffer, self.search_settings)
        self.search_context.set_highlight(False)
        self.search_mark = Gtk.TextMark()
        self.searchbar.connect("activate", self.find_next_match_from_entry)
        
        # styles
        self.stylemanager = GtkSource.StyleSchemeManager()
        self.style = self.stylemanager.get_scheme_ids()
        scheme = self.stylemanager.get_scheme(self.style[2]) 
        self.buffer.set_style_scheme(scheme)
        
        ############ styles selector #################
        btn_style_up = Gtk.Image.new_from_icon_name("down", 4)
        btn_style_up.set_name("stylesbutton")
        self.btn_styles = Gtk.MenuButton(label="Styles")
        self.btn_styles.set_tooltip_text("set Style Theme")
        self.btn_styles.set_image(btn_style_up)
        self.btn_styles.set_image_position(1)
        self.btn_styles.set_relief(Gtk.ReliefStyle.NONE)
        self.btn_styles.set_name("stylesbutton")       
        self.styles_menu = Gtk.Menu()
        self.btn_styles.set_popup(self.styles_menu) 
        self.btn_box.pack_end(self.btn_styles, False, False, 1) 
        
        for style in self.style:
            menuitem = Gtk.MenuItem(style)
            menuitem.connect("activate", self.on_styles_activated)
            self.styles_menu.append(menuitem)
        self.styles_menu.show_all()
        
        ############ templates selector #################
        templates_btn_up = Gtk.Image.new_from_icon_name("down", 4)
        templates_btn_up.set_name("dialogsbutton")
        self.btn_templates = Gtk.MenuButton(label="Templates")
        self.btn_templates.set_tooltip_text("insert template")
        self.btn_templates.set_image_position(1)
        self.btn_templates.set_image(templates_btn_up)
        self.btn_templates.set_relief(Gtk.ReliefStyle.NONE)
        self.btn_templates.set_name("dialogsbutton")       
        self.templates_menu = Gtk.Menu()
        self.btn_templates.set_popup(self.templates_menu) 
        self.btn_box.pack_end(self.btn_templates, False, False, 1) 
        mlist = []
        mypath = "templates"
        for name in listdir(mypath):
            if path.isfile(path.join(mypath, name)):
                mlist.append(name)
        mlist.sort(key=str.lower)
        
        for name in mlist:
            menuitem = Gtk.MenuItem(name.replace(".txt", ""))
            menuitem.connect("activate", self.on_templates_activated)
            self.templates_menu.append(menuitem)
        self.templates_menu.show_all()
        
        ################ definitions selector ###########################
        def_btn_up = Gtk.Image.new_from_icon_name("down", 4)
        self.def_btn = Gtk.MenuButton(label="Classes / Definitions", image=def_btn_up)
        self.def_btn.set_name("defbutton")
        self.def_btn.set_tooltip_text("go to def")
        self.def_btn.set_image_position(1)
        self.def_btn.set_relief(Gtk.ReliefStyle.NONE)
        self.def_menu = Gtk.Menu()
        self.def_btn.set_popup(self.def_menu) 
        self.btn_box.pack_end(self.def_btn, False, False, 1) 
        ##################################################################
        
        self.findbox = builder.get_object("findbox")
        
        self.replacebar = builder.get_object("replacebar")
        self.replacebar.connect("key_press_event", self.searchbar_key_press)

        ################ buttons ###########################        
        self.btn_show_find = builder.get_object("btn_show_find")
        self.btn_show_find.connect('clicked', self.toggle_findbox)
        self.btn_show_find.set_relief(Gtk.ReliefStyle.NONE)
        
        self.btn_replace = builder.get_object("btn_replace")
        self.btn_replace.connect('clicked', self.replace_one)
        self.btn_replace.set_relief(Gtk.ReliefStyle.NONE)

        self.btn_replace_all = builder.get_object("btn_replace_all")
        self.btn_replace_all.connect('clicked', self.replace_all)
        self.btn_replace_all.set_relief(Gtk.ReliefStyle.NONE)
        
        self.btn_about = builder.get_object("btn_about")
        self.btn_about.connect('clicked', self.on_about)
        self.btn_about.set_relief(Gtk.ReliefStyle.NONE)
        
        self.headerbar = builder.get_object("headerbar")
        
        self.status_label = builder.get_object("status_label")
        
        self.file_filter_text = Gtk.FileFilter()
        self.file_filter_text.set_name("Python Files")
        pattern = ["*.py", "*.py_backup"]
        for p in pattern:
            self.file_filter_text.add_pattern(p)
            
        self.file_filter_all = Gtk.FileFilter()
        self.file_filter_all.set_name("All Files")
        self.file_filter_all.add_pattern("*.*")    
       
        self.pane_widget = builder.get_object("pane_widget")
        
        # terminal
        self.terminal = Terminal()
        self.terminal.set_name("vterminal")
        self.terminal.set_size_request(-1, 100)
        self.vbox = builder.get_object("vbox")

        # add terminal to pane
        self.pane_widget.pack2(self.terminal)
        self.cb = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        
        self.win.connect("delete-event", self.on_close)
        self.win.resize(900, 800)
        self.win.move(0, 0)
        self.read_settings()
        self.win.show_all()
        h = self.win.get_allocation().height
        self.pane_widget.set_position(h - 350)
        self.findbox.set_visible(False)

        ### load sys.argv file
        if len(sys.argv) > 1:
            myfile = sys.argv[1]
            self.open_file(myfile)
        else:
            self.status_label.set_text("Welcome to PyEdit4")
            
        # focus on editor
        self.editor.grab_focus()
        self.is_changed = False
        Gtk.main() 
        
    def editor_key_press(self, widget, event):
        if (event.keyval == Gdk.keyval_from_name("n") and
            event.state == Gdk.ModifierType.CONTROL_MASK):
            self.on_new_file()
        if (event.keyval == Gdk.keyval_from_name("o") and
            event.state == Gdk.ModifierType.CONTROL_MASK):
            self.on_open_file()
        if (event.keyval == Gdk.keyval_from_name("s") and
            event.state == Gdk.ModifierType.CONTROL_MASK):
            self.save_file()
        if (event.keyval == Gdk.keyval_from_name("F5")):
            self.on_run()
        if (event.keyval == Gdk.keyval_from_name("f") and
            event.state == Gdk.ModifierType.CONTROL_MASK):
            self.find_text()
        if (event.keyval == Gdk.keyval_from_name("q") and
            event.state == Gdk.ModifierType.CONTROL_MASK):
            self.on_close()
        if (event.keyval == Gdk.keyval_from_name("F2")):
            self.on_toggle_comment()
        if (event.keyval == Gdk.keyval_from_name("F9")):
            self.find_previous_match()
        if (event.keyval == Gdk.keyval_from_name("F10")):
            self.find_next_match()
        if (event.keyval == Gdk.keyval_from_name("F1")):
            self.show_dev_help()
        if (event.keyval == Gdk.keyval_from_name("F7")):
            self.on_unindent_lines()
        if (event.keyval == Gdk.keyval_from_name("F8")):
            self.on_indent_lines()

    def searchbar_key_press(self, widget, event):
        if (event.keyval == Gdk.KEY_Escape):
            self.findbox.set_visible(False)
            
    # drop file
    def on_drag_data_received(self, widget, context, x, y, selection, target_type, timestamp):
        myfile = ""
        if target_type == 80:
            uri = str(selection.get_data().decode().rstrip())
            myfile = url2pathname(uri)[7:]
            print(f'dropped file: {myfile}')
            if self.is_changed:
                self.maybe_saved()
                self.open_file(myfile)
            else:
                self.open_file(myfile)
        else:
            txt = selection.get_text()
            self.buffer.insert_at_cursor(txt)
                
    # open file            
    def open_file(self, myfile, *args):
        with open(myfile, 'r') as f:
            if myfile:
                data = f.read()
                self.buffer.set_text(data)           
                self.editor.set_buffer(self.buffer)
                self.current_file = myfile
                self.current_filename = myfile.rpartition("/")[2]
                self.current_folder = path.dirname(myfile)
                f.close()
                self.headerbar.set_subtitle(myfile)
                self.status_label.set_text(f"'{myfile}' loaded")
                self.headerbar.set_title("PyEdit4")
                self.editor.grab_focus()
                self.is_changed = False
                self.lastfiles.append(myfile)
                self.ordered_list()
                self.terminal.reset(True, True)
                self.fill_def_btn()
        
    # get editor text
    def get_buffer(self):
        start_iter = self.buffer.get_start_iter()
        end_iter = self.buffer.get_end_iter()
        text = self.buffer.get_text(start_iter, end_iter, True) 
        return text
    
    # replace one  
    def replace_one(self, *args):
        if len(self.searchbar.get_text()) > 0:
            print("replace_one")
            search_text = self.searchbar.get_text()
            replace_text = self.replacebar.get_text()
            start_iter = self.buffer.get_start_iter()
            end_iter = self.buffer.get_end_iter()
            found = start_iter.forward_search(search_text, Gtk.TextSearchFlags(1), end_iter)
            if found:
                match_start,match_end = found
                self.buffer.select_range(match_start,match_end)
                
                self.buffer.insert_at_cursor(self.replacebar.get_text(), len(self.replacebar.get_text()))
                self.buffer.delete_selection(True, True)
                self.status_label.set_text(f"replaced '{search_text}' with '{replace_text}'")

    # replace all
    def replace_all(self, *args):
        if len(self.searchbar.get_text()) > 0:
            print("replace_all")
            search_text = self.searchbar.get_text()
            replace_text = self.replacebar.get_text()
            self.status_label.set_text(f"replaced all '{search_text}' with '{replace_text}'")
            text = self.get_buffer()
            text = text.replace(search_text, replace_text)
            self.buffer.set_text(text)

    # searchbox
    def find_text(self, start_offset=1):
        if not self.findbox.is_visible():
            self.findbox.set_visible(True)
        self.searchbar.set_text("")
        self.searchbar.grab_focus()            
        if self.buffer.get_has_selection():
            a,b  = self.buffer.get_selection_bounds()
            mark = self.buffer.get_text(a, b, True)
            self.searchbar.set_text(mark)
        buf = self.buffer
        insert = buf.get_iter_at_mark(buf.get_insert())
        start, end = buf.get_bounds()
        insert.forward_chars(start_offset)
        match, start_iter, end_iter, wrapped = self.search_context.forward2(insert)

        if match:
            buf.place_cursor(start_iter)
            buf.move_mark(buf.get_selection_bound(), end_iter)
            self.editor.scroll_to_mark(buf.get_insert(), 0.25, True, 0.5, 0.5)
            return True
        else:
            buf.place_cursor(buf.get_iter_at_mark(buf.get_insert()))

    # show / hide findbox
    def toggle_findbox(self, *args):
        if not self.findbox.is_visible():
            self.findbox.set_visible(True)
        else:
            self.findbox.set_visible(False)
            
    # set modified   
    def is_modified(self, *args):
        self.is_changed = True
        self.headerbar.set_title("PyEdit4*")
    
    # new file clear editor
    def on_new_file(self, *args):
        if self.is_changed:
            self.maybe_saved()
            self.buffer.set_text(self.new_text)
            self.editor.set_buffer(self.buffer)
            self.current_file = ""
            self.current_filename = ""
            self.headerbar.set_title("PyEdit4") 
            self.headerbar.set_subtitle("New")
            self.is_changed = False
        else:
            self.buffer.set_text(self.new_text)
            self.editor.set_buffer(self.buffer)
            self.current_file = ""
            self.current_filename = ""
            self.headerbar.set_title("PyEdit4")
            self.headerbar.set_subtitle("New")    
            self.is_changed = False
            
    # open file    
    def on_open(self, *args):       
        if self.is_changed:
            self.maybe_saved()
            self.on_open_file()
            self.is_changed = False
        else:
            self.on_open_file()
            self.is_changed = False

    # open file dialog    
    def on_open_file(self, *args):
        myfile = ""
        dlg = Gtk.FileChooserDialog(title="Please choose a file", parent=None, action = 0)
        dlg.add_buttons("Cancel", Gtk.ResponseType.CANCEL,
             "Open", Gtk.ResponseType.OK)
        dlg.add_filter(self.file_filter_text)
        dlg.add_filter(self.file_filter_all)
        dlg.set_current_folder(self.current_folder)
        response = dlg.run()

        if response == Gtk.ResponseType.OK:
            myfile = dlg.get_filename()
        else:
            myfile = ("")

        dlg.destroy()    
        
        
        if not myfile == "":
            dst = f"{path.abspath(myfile)}_bak"
            copyfile(myfile, dst)
            self.open_file(myfile)

    # file save as ...
    def on_save_file(self, *args):
        myfile = ""
        dlg = Gtk.FileChooserDialog(title="Please choose a file", parent=None, action = 1)
        dlg.add_buttons("Cancel", Gtk.ResponseType.CANCEL,
             "Save", Gtk.ResponseType.OK)
        dlg.set_do_overwrite_confirmation (True)     
        dlg.add_filter(self.file_filter_text)
        dlg.add_filter(self.file_filter_all)
        if self.current_filename == "":
            dlg.set_current_name("new.py")
        else:
            dlg.set_current_folder(path.dirname(self.current_file))
            dlg.set_current_name(self.current_filename)
        response = dlg.run()

        if response == Gtk.ResponseType.OK:
            myfile = dlg.get_filename()
            
        else:
            myfile = ("")
            
        dlg.destroy()
        if not myfile == "":
            print("saving", myfile)

            with open(myfile, 'w') as f:
                text = self.get_buffer()
                f.write(text)
                f.close()
                self.status_label.set_text(f"'{myfile}' saved")
                self.current_file = myfile
                self.current_filename = myfile.rpartition("/")[2]
                self.current_folder = path.dirname(myfile)
                self.is_changed = False
                self.headerbar.set_title("PyEdit4")
                self.headerbar.set_subtitle(myfile)
                self.lastfiles.append(myfile)
                self.ordered_list()
                self.fill_def_btn()
                
    # save current file            
    def save_file(self, *args):
        myfile = self.current_file
        if not myfile == "":
            with open(myfile, 'w') as f:
                text = self.get_buffer()
                f.write(text)
                f.close()
                self.status_label.set_text(f"'{myfile}' saved")
                self.current_file = myfile
                self.current_filename = myfile.rpartition("/")[2]
                self.current_folder = path.dirname(myfile)
                self.is_changed = False 
                self.headerbar.set_title("PyEdit4")
                self.headerbar.set_subtitle(myfile)
        else:
            self.on_save_file()
        return True

    # ask to save changes
    def maybe_saved(self, *args):
        print("is modified", self.is_changed)
        md = Gtk.MessageDialog(title="PyEdit4", 
                                text="The document was changed.\n\nSave changes?", 
                                parent=None, buttons=("Cancel", Gtk.ResponseType.CANCEL,
             "Yes", Gtk.ResponseType.YES, "No", Gtk.ResponseType.NO))
        md.set_image(self.q_icon)
        response = md.run()
        if response == Gtk.ResponseType.YES:
            ### save
            self.save_file()
            md.destroy()
            return False
        elif response == Gtk.ResponseType.NO:
            md.destroy()
            return False
        elif response == Gtk.ResponseType.CANCEL:
            md.destroy()
            return True
        md.destroy()
        
    # close window
    def on_close(self, *args):
        print("goodbye ...")
        self.write_settings()
        print(f"{self.current_file} changed: {self.is_changed}")
        if self.is_changed:
            b = self.maybe_saved()
            print (f"close: {b}")
            if b: 
                return True
            else:
                Gtk.main_quit()
        else:
            Gtk.main_quit()

    # run script
    def on_run(self, *args):
        # check code exists
        code = self.get_buffer()
        if not code == self.new_text:
            if self.is_changed:
                self.save_file()
                
            # set working dir
            wd = path.dirname(self.current_file)
            self.cb.set_text(f"cd {wd}", -1)
            self.terminal.paste_clipboard()
            self.terminal.feed_child([13])
            # run script
            cmd = f"python3 '{self.current_file}'"
            print(cmd)
            self.cb.set_text(cmd, -1)
            self.terminal.paste_clipboard()
            self.terminal.grab_focus()
            self.terminal.feed_child([13])
        else:
            self.status_label.set_text("no code to execute!")
        self.editor.grab_focus()

    # open script folder in filemanager
    def on_fm(self, *args):
        wd = path.dirname(self.current_file)
        run(["xdg-open", wd])

    # set comment / remove comment    
    def on_toggle_comment(self, *args):
        if self.buffer.get_has_selection():
            # block comment / uncomment
            buf_list = []
            buf_old = self.get_selected_buffer()
            self.buffer.delete_selection(True, True)
            for line in buf_old.splitlines():
                if not line.startswith("#"):
                    buf_list.append(f"#{line}")
                else:
                    buf_list.append(f"{line[1:]}")
            buf_new = "\n".join(buf_list)        
            self.buffer.insert_at_cursor(buf_new, -1)
        else:     
            # single line comment / uncomment
            mark = self.buffer.get_insert()
            iter = self.buffer.get_iter_at_mark(mark)
            line_number = iter.get_line()
            cursor = self.buffer.get_iter_at_line(line_number)
            cursor.backward_sentence_starts(0)
            self.buffer.place_cursor(cursor)
            mark = self.buffer.get_insert()
            iter = self.buffer.get_iter_at_mark(mark)
            if not iter.get_char() == "#":
                self.buffer.insert(iter, "#")
            else:
                mark = self.buffer.get_insert()
                iter = self.buffer.get_iter_at_mark(mark)
                line_number = iter.get_line()
                cursor = self.buffer.get_iter_at_line(line_number)
                cursor.forward_cursor_positions(1)
                self.buffer.place_cursor(cursor)
                next_mark = self.buffer.get_insert()
                next_iter = self.buffer.get_iter_at_mark(next_mark)
                self.buffer.delete(iter,next_iter)
     
    # find from searchbar 
    def find_next_match_from_entry(self, *args):
        search_str =  self.searchbar.get_text()
        self.search_settings.set_search_text(search_str)
        self.search_mark = self.buffer.get_insert()
        search_iter = self.buffer.get_iter_at_mark (self.search_mark)
        search_iter.forward_char()
        result = self.search_context.forward(search_iter)
        valid, start_iter, end_iter = result[0], result[1], result[2]
        if valid == True:
            self.buffer.move_mark(self.search_mark, end_iter)
            self.buffer.select_range(start_iter, end_iter)
            self.editor.scroll_to_iter(end_iter, 0.1, True, 0.0, 0.1)

    # find next from selected
    def find_next_match(self, *args):
        if self.buffer.get_has_selection():
            a,b  = self.buffer.get_selection_bounds()
            mark = self.buffer.get_text(a, b, True)
            self.search_settings.set_search_text(mark)
            self.search_mark = self.buffer.get_insert()
            search_iter = self.buffer.get_iter_at_mark (self.search_mark)
            search_iter.forward_char()
            result = self.search_context.forward(search_iter)
            valid, start_iter, end_iter = result[0], result[1], result[2]
            if valid == True:
                self.buffer.move_mark(self.search_mark, end_iter)
                self.buffer.select_range(start_iter, end_iter)
                self.editor.scroll_to_iter(end_iter, 0.1, True, 0.0, 0.1)
                
    # find previous from selected    
    def find_previous_match(self, *args):
        if self.buffer.get_has_selection():
            a,b  = self.buffer.get_selection_bounds()
            mark = self.buffer.get_text(a, b, True)
            self.search_settings.set_search_text(mark)
            self.search_mark = self.buffer.get_insert()
            search_iter = self.buffer.get_iter_at_mark (self.search_mark)
            search_iter.forward_char()
            result = self.search_context.backward(search_iter)
            valid, start_iter, end_iter = result[0], result[1], result[2]
            if valid == True:
                self.buffer.move_mark(self.search_mark, end_iter)
                self.buffer.select_range(start_iter, end_iter)
                self.editor.scroll_to_iter(end_iter, 0.1, True, 0.0, 0.1)

    # go to line
    def on_goto_line(self, *args):
        print("editing_done")
        line_number = int(self.entry_goto.get_text()) - 1
        cursor = self.buffer.get_iter_at_line(line_number)
        cursor.backward_sentence_starts(0)
        self.buffer.place_cursor(cursor)
        mark = self.buffer.get_insert()
        iter = self.buffer.get_iter_at_mark(mark)        
        self.editor.scroll_to_iter(iter, 0.0, True, 0.0, 0.0)

    # about dialog
    def on_about(self, *args):
        dialog = Gtk.AboutDialog()
        dialog.set_title("PyEdit4")
        dialog.set_version("1.0")
        dialog.set_program_name("PyEdit4")
        dialog.set_authors(["Axel Schneider"])
        dialog.set_website("https://github.com/Axel-Erfurt/PyEdit4")
        dialog.set_website_label("github Project Site")
        dialog.set_comments("Python Gtk+3 Editor")
        dialog.set_copyright("© 2021 Axel Schneider")
        dialog.set_license_type(Gtk.License(12))
        dialog.set_wrap_license(True)
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale("pyedit4.png", 128, 128, True)
        dialog.set_logo(pixbuf)
        dialog.set_modal(True)
        dialog.connect('response', lambda dialog, data: dialog.destroy())
        dialog.show_all()

    # read config
    def read_settings(self, *args):
        if self.config.has_section("window"):
            x, y, w, h = (self.config['window']['left'], self.config['window']['top'], 
                                self.config['window']['width'], self.config['window']['height'])
            self.win.resize(int(w), int(h))
            self.win.move(int(x), int(y))
            style = self.config['window']['style']
            scheme = self.stylemanager.get_scheme(style) 
            self.buffer.set_style_scheme(scheme)           
        if self.config.has_section("files"):
            self.lastfiles = self.config['files']['lastfiles'].split(",")
            self.ordered_list()
    
    # write config
    def write_settings(self, *args):
        self.config['window']['left'] = str(self.win.get_position()[0])
        self.config['window']['top'] = str(self.win.get_position()[1])
        self.config['window']['width'] = str(self.win.get_size()[0])
        self.config['window']['height'] = str(self.win.get_size()[1])
        self.config['window']['style'] = self.buffer.get_style_scheme().get_id()
        self.config['files']['lastfiles'] = ",".join(self.lastfiles)
        with open('config.conf', 'w') as configfile:
            self.config.write(configfile)

    # check code for unused imports / errors
    def on_check_code(self, *args):
        if not self.current_file == "":
            wd = path.dirname(sys.argv[0])
            check = path.join(wd, "checkmycode")
            cmd = f"{check} '{self.current_file}'"
            run(cmd, shell = True)
        else:
            self.status_label.set_text("no code!")

    # clean recent files list
    def ordered_list(self, *args):
        for i in self.recent_menu.get_children():
            self.recent_menu.remove(i)
        self.lastfiles = [x for x in self.lastfiles if x]
        #self.lastfiles = self.lastfiles[:10]
        self.lastfiles = self.ordered_set(self.lastfiles)
        for line in self.lastfiles:
            if not line.startswith("/tmp"):
                menuitem = Gtk.MenuItem(line)
                menuitem.connect("activate", self.on_menuitem_activated)
                self.recent_menu.append(menuitem)
        self.recent_menu.show_all()
            
        
    def ordered_set(self, in_list):
        out_list = []
        added = set()
        for val in in_list:
            if not val in added:
                out_list.append(val)
                added.add(val)
        return out_list

    # color dialog    
    def on_get_color(self, *args): 
        colorchooserdialog = Gtk.ColorChooserDialog()
        colorchooserdialog.set_property("show-editor", False)

        if colorchooserdialog.run() == Gtk.ResponseType.OK:
            color = colorchooserdialog.get_rgba()
            red = (color.red * 255)
            green = (color.green * 255)
            blue = (color.blue * 255)
            col = ("#{0:X}{1:X}{2:X}".format(int(red), int(green), int(blue)))
            self.buffer.delete_selection(True, True)
            self.buffer.insert_at_cursor(col, -1)
            self.editor.grab_focus() 
        colorchooserdialog.destroy()

    # get selected text
    def get_selected_buffer(self, *args):
        a,b  = self.buffer.get_selection_bounds()
        sel_text = self.buffer.get_text(a, b, True)
        return (sel_text) 

    # recent files menu
    def on_menuitem_activated(self, menuitem, *args):
        if self.is_changed:
            self.maybe_saved()
        myfile = menuitem.get_label()
        if path.isfile(myfile):
            self.open_file(myfile) 
        else:
            self.message_dialog("File does not exist")

    # styles menu
    def on_styles_activated(self, menuitem, *args):
        style = menuitem.get_label()
        scheme = self.stylemanager.get_scheme(style) 
        self.buffer.set_style_scheme(scheme)
        print(self.buffer.get_style_scheme().get_id())

    # templates menu    
    def on_templates_activated(self, menuitem, *args):
        text_to_insert = open(f"templates/{menuitem.get_label()}.txt").read()
        self.buffer.insert_at_cursor(text_to_insert)
        self.fill_def_btn()

    # message dialog    
    def message_dialog(self, message, *args):
        dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.INFO,
                                    Gtk.ButtonsType.OK, "Message")
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy() 

    # show devhelp    
    def show_dev_help(self, *args):
        if self.can_devhelp:
            help_text = self.get_selected_buffer()
            Popen(["devhelp", "-s", help_text])

    def on_resize(self, *args):
        print("move-handle")

    # indent lines    
    def on_indent_lines(self, *args):
        a,b  = self.buffer.get_selection_bounds()
        self.editor.indent_lines(a, b)
        
    # unindent lines 
    def on_unindent_lines(self, *args):
        a,b  = self.buffer.get_selection_bounds()
        self.editor.unindent_lines(a, b)

    # fill classes / def menu
    def fill_def_btn(self, *args):
        for i in self.def_menu.get_children():
            self.def_menu.remove(i)
        text_list = self.get_buffer().splitlines()
        for line in text_list:
            if ("def ") in line or "class " in line:
                menuitem = Gtk.MenuItem(line)
                menuitem.connect("activate", self.on_def_activated)
                self.def_menu.append(menuitem)
        self.def_menu.show_all()     

    # classes / def menu
    def on_def_activated(self, menuitem, *args):
        def_text = menuitem.get_label()
        start_iter =  self.buffer.get_start_iter()
        found = start_iter.forward_search(def_text,0, None) 
        if found:
           match_start,match_end = found
           self.buffer.select_range(match_start,match_end)
           self.editor.scroll_to_iter(match_end, 0.0, True, 0.0, 0.0)
           self.editor.grab_focus()        
    
        
if __name__ == "__main__":
    w = MyWindow()
    w.main(sys.argv)
    
