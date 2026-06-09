import sys
import os

# TRIK JEMBATAN 2026: Membuat modul pkg_resources tiruan agar pyrebase tidak crash di Vercel
from types import ModuleType

class MockPkgResources(ModuleType):
    def get_distribution(self, dist):
        class MockDist:
            version = "3.0.0"
        return MockDist()

# Suntikkan pkg_resources palsu ke dalam sistem memori Python sebelum pyrebase di-import
sys.modules['pkg_resources'] = MockPkgResources('pkg_resources')

# Setelah sistem aman dari crash, panggil aplikasi Flask asli Anda
from flask_app import app as application