import os
import asyncio
import json
from pathlib import Path
import random
import subprocess
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.gridlayout import GridLayout
from kivy.clock import Clock
from kivy.core.window import Window
import threading

Window.clearcolor = (0, 0, 0, 1)

try:
    from telethon import TelegramClient
    from telethon.sessions import StringSession
    from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
    TELETHON_AVAILABLE = True
except ImportError:
    TELETHON_AVAILABLE = False

API_ID = 27737241
API_HASH = "8edb749d2f65741c5f32dba2ba622c21"
SESSION_DIR = "sessions"
SESSION_FILE = "faust.session"
CONFIG_FILE = "config.json"

device_models = [
    "Samsung Galaxy S21", "Samsung Galaxy S22 Ultra", "Xiaomi Redmi Note 10 Pro",
    "Google Pixel 6 Pro", "OnePlus 9 Pro"
]

class AuthScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()
        self.phone_code = ""
        self.client = None
        self.phone = ""
    
    def build_ui(self):
        layout = BoxLayout(orientation='vertical', padding=40, spacing=20)
        
        title = Label(
            text='Авторизация',
            font_size='24sp',
            color=(0.75, 0.75, 0.75, 1),
            size_hint_y=0.2
        )
        layout.add_widget(title)
        
        self.phone_input = TextInput(
            hint_text='+79123456789',
            multiline=False,
            background_color=(0.1, 0.1, 0.1, 1),
            foreground_color=(1, 1, 1, 1),
            size_hint_y=0.1
        )
        layout.add_widget(self.phone_input)
        
        self.send_phone_btn = Button(
            text='ОТПРАВИТЬ КОД',
            background_color=(0.07, 0.07, 0.07, 1),
            color=(1, 1, 1, 1),
            size_hint_y=0.1
        )
        self.send_phone_btn.bind(on_press=self.send_phone)
        layout.add_widget(self.send_phone_btn)
        
        self.code_label = Label(
            text='Код: ',
            font_size='20sp',
            color=(1, 1, 1, 1),
            size_hint_y=0.1
        )
        layout.add_widget(self.code_label)
        
        self.numpad = self.create_numpad()
        layout.add_widget(self.numpad)
        
        self.confirm_btn = Button(
            text='ПОДТВЕРДИТЬ',
            background_color=(0.2, 0.2, 0.2, 1),
            color=(1, 1, 1, 1),
            size_hint_y=0.1,
            disabled=True
        )
        self.confirm_btn.bind(on_press=self.confirm_code)
        layout.add_widget(self.confirm_btn)
        
        self.add_widget(layout)
    
    def create_numpad(self):
        grid = GridLayout(cols=3, spacing=10, size_hint_y=0.4)
        
        for i in range(1, 10):
            btn = Button(
                text=str(i),
                background_color=(0.07, 0.07, 0.07, 1),
                color=(1, 1, 1, 1)
            )
            btn.bind(on_press=lambda instance, digit=i: self.add_digit(digit))
            grid.add_widget(btn)
        
        zero_btn = Button(
            text='0',
            background_color=(0.07, 0.07, 0.07, 1),
            color=(1, 1, 1, 1)
        )
        zero_btn.bind(on_press=lambda instance: self.add_digit(0))
        grid.add_widget(zero_btn)
        
        clear_btn = Button(
            text='ОЧИСТИТЬ',
            background_color=(0.3, 0.1, 0.1, 1),
            color=(1, 1, 1, 1)
        )
        clear_btn.bind(on_press=self.clear_code)
        grid.add_widget(clear_btn)
        
        return grid
    
    def add_digit(self, digit):
        if len(self.phone_code) < 10:
            self.phone_code += str(digit)
            self.update_code_display()
    
    def clear_code(self, instance):
        self.phone_code = ""
        self.update_code_display()
    
    def update_code_display(self):
        self.code_label.text = f'Код: {self.phone_code}'
        self.confirm_btn.disabled = len(self.phone_code) < 5
    
    def send_phone(self, instance):
        if not TELETHON_AVAILABLE:
            self.show_error("Telethon не установлен")
            return
        
        phone = self.phone_input.text.strip()
        if not (phone.startswith("+") and phone[1:].isdigit() and len(phone) > 5):
            self.show_error("Неверный формат номера")
            return
        
        self.phone = phone
        self.send_phone_btn.disabled = True
        self.send_phone_btn.text = "ОТПРАВКА..."
        
        threading.Thread(target=self.send_code_request, daemon=True).start()
    
    def send_code_request(self):
        try:
            device_model = random.choice(device_models)
            self.client = TelegramClient(StringSession(), API_ID, API_HASH, device_model=device_model)
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def connect_and_send():
                await self.client.connect()
                await self.client.send_code_request(self.phone)
            
            loop.run_until_complete(connect_and_send())
            loop.close()
            
            Clock.schedule_once(lambda dt: self.on_code_sent())
            
        except Exception as e:
            Clock.schedule_once(lambda dt: self.on_code_error(str(e)))
    
    def on_code_sent(self):
        self.send_phone_btn.text = "КОД ОТПРАВЛЕН"
        self.send_phone_btn.background_color = (0.1, 0.3, 0.1, 1)
    
    def on_code_error(self, error):
        self.send_phone_btn.disabled = False
        self.send_phone_btn.text = "ОТПРАВИТЬ КОД"
        self.show_error(f"Ошибка: {error}")
    
    def confirm_code(self, instance):
        if not self.client or len(self.phone_code) < 5:
            return
        
        self.confirm_btn.disabled = True
        self.confirm_btn.text = "АВТОРИЗАЦИЯ..."
        
        threading.Thread(target=self.authenticate, daemon=True).start()
    
    def authenticate(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def sign_in():
                try:
                    await self.client.sign_in(phone=self.phone, code=self.phone_code)
                    await self.save_session()
                    return True, None
                except SessionPasswordNeededError:
                    return False, "Требуется пароль 2FA"
                except PhoneCodeInvalidError:
                    return False, "Неверный код"
                except Exception as e:
                    return False, str(e)
            
            success, error = loop.run_until_complete(sign_in())
            loop.close()
            
            if success:
                Clock.schedule_once(lambda dt: self.on_auth_success())
            else:
                Clock.schedule_once(lambda dt: self.on_auth_error(error))
            
        except Exception as e:
            Clock.schedule_once(lambda dt: self.on_auth_error(str(e)))
    
    async def save_session(self):
        session_str = StringSession.save(self.client.session)
        
        sessions_dir = Path("faust_tool") / SESSION_DIR
        sessions_dir.mkdir(parents=True, exist_ok=True)
        
        session_file = sessions_dir / SESSION_FILE
        session_file.write_text(session_str, encoding='utf-8')
        
        config = {"API_ID": API_ID, "API_HASH": API_HASH}
        config_file = Path("faust_tool") / CONFIG_FILE
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        
        await self.client.disconnect()
    
    def on_auth_success(self):
        app = App.get_running_app()
        app.show_main_screen()
    
    def on_auth_error(self, error):
        self.confirm_btn.disabled = False
        self.confirm_btn.text = "ПОДТВЕРДИТЬ"
        self.show_error(error)
    
    def show_error(self, message):
        self.code_label.text = f"Ошибка: {message}"
        self.code_label.color = (1, 0.3, 0.3, 1)

class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()
        self.bot_process = None
    
    def build_ui(self):
        layout = BoxLayout(orientation='vertical', padding=40, spacing=30)
        
        title = Label(
            text='Faust Tool',
            font_size='36sp',
            color=(0.75, 0.75, 0.75, 1),
            size_hint_y=0.4
        )
        layout.add_widget(title)
        
        self.status_label = Label(
            text='Статус: Остановлен',
            font_size='18sp',
            color=(1, 1, 1, 1),
            size_hint_y=0.1
        )
        layout.add_widget(self.status_label)
        
        btn_layout = BoxLayout(orientation='vertical', spacing=15, size_hint_y=0.3)
        
        self.start_btn = Button(
            text='ЗАПУСК',
            background_color=(0.07, 0.07, 0.07, 1),
            color=(1, 1, 1, 1),
            size_hint_y=0.5
        )
        self.start_btn.bind(on_press=self.toggle_bot)
        btn_layout.add_widget(self.start_btn)
        
        self.about_btn = Button(
            text='О ПРИЛОЖЕНИИ',
            background_color=(0.07, 0.07, 0.07, 1),
            color=(1, 1, 1, 1),
            size_hint_y=0.5
        )
        self.about_btn.bind(on_press=self.show_about)
        btn_layout.add_widget(self.about_btn)
        
        layout.add_widget(btn_layout)
        
        self.add_widget(layout)
    
    def toggle_bot(self, instance):
        if self.bot_process and self.bot_process.poll() is None:
            self.stop_bot()
        else:
            self.start_bot()
    
    def start_bot(self):
        if not self.check_session():
            app = App.get_running_app()
            app.show_auth_screen()
            return
        
        if not self.validate_session():
            self.delete_session()
            self.status_label.text = "Сессия невалидна. Нужна повторная авторизация"
            self.status_label.color = (1, 0.5, 0, 1)
            Clock.schedule_once(lambda dt: app.show_auth_screen(), 2)
            return
        
        try:
            self.bot_process = subprocess.Popen([
                "python", "-m", "faust_tool.userbot"
            ], cwd="faust_tool")
            
            self.start_btn.text = "СТОП"
            self.start_btn.background_color = (0.3, 0.1, 0.1, 1)
            self.status_label.text = "Статус: Запущен"
            self.status_label.color = (0.3, 1, 0.3, 1)
            
        except Exception as e:
            self.status_label.text = f"Ошибка: {str(e)}"
            self.status_label.color = (1, 0.3, 0.3, 1)
    
    def stop_bot(self):
        if self.bot_process:
            self.bot_process.terminate()
            self.bot_process = None
        
        self.start_btn.text = "ЗАПУСК"
        self.start_btn.background_color = (0.07, 0.07, 0.07, 1)
        self.status_label.text = "Статус: Остановлен"
        self.status_label.color = (1, 1, 1, 1)
    
    def check_session(self):
        session_file = Path("faust_tool") / SESSION_DIR / SESSION_FILE
        return session_file.exists()
    
    def validate_session(self):
        if not self.check_session():
            return False
        
        try:
            session_file = Path("faust_tool") / SESSION_DIR / SESSION_FILE
            session_str = session_file.read_text(encoding='utf-8')
            
            client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def check_connection():
                await client.connect()
                if await client.is_user_authorized():
                    await client.disconnect()
                    return True
                await client.disconnect()
                return False
            
            result = loop.run_until_complete(check_connection())
            loop.close()
            return result
            
        except Exception:
            return False
    
    def delete_session(self):
        try:
            session_file = Path("faust_tool") / SESSION_DIR / SESSION_FILE
            config_file = Path("faust_tool") / CONFIG_FILE
            
            if session_file.exists():
                session_file.unlink()
            if config_file.exists():
                config_file.unlink()
        except Exception:
            pass
    
    def show_about(self, instance):
        app = App.get_running_app()
        app.show_about_screen()

class AboutScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()
    
    def build_ui(self):
        layout = BoxLayout(orientation='vertical', padding=40, spacing=20)
        
        title = Label(
            text='О ПРИЛОЖЕНИИ',
            font_size='24sp',
            color=(0.75, 0.75, 0.75, 1),
            size_hint_y=0.1
        )
        layout.add_widget(title)
        
        about_text = (
            "Faust Tool — это Telegram-юзербот с собственным лаунчером.\n\n"
            "Приложение позволяет:\n"
            "Авторизоваться в Telegram и сохранить сессию\n"
            "Запускать и останавливать юзербота одной кнопкой\n"
            "Управлять ботом прямо с телефона\n\n"
            "Юзербот работает в фоне, используя библиотеку Telethon.\n\n"
            "Версия: 1.0\n"
            "Автор: faust"
        )
        
        about_label = Label(
            text=about_text,
            font_size='16sp',
            color=(1, 1, 1, 1),
            size_hint_y=0.7,
            text_size=(None, None),
            halign='left',
            valign='top'
        )
        layout.add_widget(about_label)
        
        back_btn = Button(
            text='НАЗАД',
            background_color=(0.07, 0.07, 0.07, 1),
            color=(1, 1, 1, 1),
            size_hint_y=0.1
        )
        back_btn.bind(on_press=self.go_back)
        layout.add_widget(back_btn)
        
        self.add_widget(layout)
    
    def go_back(self, instance):
        app = App.get_running_app()
        app.show_main_screen()

class FaustToolApp(App):
    def build(self):
        self.sm = ScreenManager()
        
        session_file = Path("faust_tool") / SESSION_DIR / SESSION_FILE
        if session_file.exists():
            self.show_main_screen()
        else:
            self.show_auth_screen()
        
        return self.sm
    
    def show_auth_screen(self):
        self.sm.clear()
        self.sm.add_widget(AuthScreen(name='auth'))
        self.sm.current = 'auth'
    
    def show_main_screen(self):
        self.sm.clear()
        self.sm.add_widget(MainScreen(name='main'))
        self.sm.current = 'main'
    
    def show_about_screen(self):
        self.sm.add_widget(AboutScreen(name='about'))
        self.sm.current = 'about'

if __name__ == '__main__':
    FaustToolApp().run()