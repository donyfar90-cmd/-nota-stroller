[app]
title = Nota Stroller
package.name = notastroller
package.domain = org.donyfar

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,html,db
source.exclude_dirs = tests,bin,.buildozer,.git,__pycache__

version = 0.1

requirements = python3,kivy,flask
android.additional_requirements = libffi

orientation = portrait
fullscreen = 0

android.permissions = INTERNET
android.api = 33
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True
android.archs = arm64-v8a

p4a.branch = master
log_level = 2
