from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.graphics import PushMatrix, PopMatrix, Rotate
from kivy.properties import NumericProperty
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.properties import ListProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color, Rectangle
from kivy.properties import ListProperty, StringProperty, ColorProperty
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.factory import Factory
from kivymd.uix.button import MDIconButton
Factory.register('MDIconButton', cls=MDIconButton)
# Set window size before running the app
Window.size = (340, 420)
from kivymd.app import MDApp  # <- Import MDApp, not App
from kivy.uix.recycleview import RecycleView



# --- KV String (with the corrected order) ---


# --- Python Classes (MessageBubble is simplified) ---

class MessageBubble(BoxLayout):
    # No need for __init__ here, KV handles the logic
    role = StringProperty()
    content = StringProperty()
    bg_color = ColorProperty([0.2, 0.6, 0.8, 1])

    def on_role(self, instance, value):
        # This method is called automatically when the 'role' property changes
        if value == 'user':
            self.bg_color = (0.2, 0.6, 0.8, 1)
            self.ids.label.color = (1, 1, 1, 1)
            self.pos_hint = {'right': 1}
        else: # assistant
            self.bg_color = (0.85, 0.85, 0.85, 1)
            self.ids.label.color = (0, 0, 0, 1)
            self.pos_hint = {'x': 0}

class SettingsMenu(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        pass
class ChatBox(BoxLayout):
    messages = []

    def update_message(self, messages):
        self.messages=messages
        # Scroll to the bottom to show the new message
        self.ids.rv.data = self.messages  # <-- this is critical
        Clock.schedule_once(lambda dt: setattr(self.ids.rv, 'scroll_y', 0), 0.1)
    def schedule_scroll(self, *args):
        """
        This method is called by the on_data event in the KV rule.
        It waits one frame to ensure the layout is updated, then scrolls.
        """
        Clock.schedule_once(lambda dt: setattr(self.ids.rv, 'scroll_y', 0))
class ChatMenu(Screen):
     def __init__(self, **kwargs):
        super().__init__(**kwargs)
        messages=[{"role":"assistant","content":"this is a long messages !!!!!!!!!!"}]
        layout = BoxLayout(orientation='vertical')
        self.chat=ChatBox()
        self.chat.update_message(messages)
        layout.add_widget(self.chat)
        
        self.add_widget(layout)
        


class MyApp(MDApp):
    def build(self):
        return Builder.load_file("ui.kv")
        

MyApp().run()
