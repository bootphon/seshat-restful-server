from app import app
from tools.configs import ProductionConfig
from mongoengine import connect

if __name__ == "__main__":
    connect("seshat_prod")
    app.config.from_object(ProductionConfig)
    app.run()

