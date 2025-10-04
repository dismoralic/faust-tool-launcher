[app]
title = Faust Tool
package.name = fausttool
package.domain = org.faust

version = 1.0
requirements = python3, kivy, telethon, openssl, cryptography

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,txt,json

[buildozer]
log_level = 2

android.permissions = INTERNET, ACCESS_NETWORK_STATE
android.api = 33
android.minapi = 21