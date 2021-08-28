import scraper
from flask import Flask
from flask_restful import Api, Resource

app = Flask(__name__)
api = Api(app)


class RevTec(Resource):
    def get(self, placa):
        a = scraper.analizar_respuesta(placa, scraper.extract(placa, 0))
        return a


api.add_resource(RevTec, "/<string:placa>")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
