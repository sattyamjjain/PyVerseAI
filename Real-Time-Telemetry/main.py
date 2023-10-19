from flask import Flask, request, jsonify
from db import MeterValueRepo

app = Flask(__name__)


@app.route("/list", methods=["GET"])
def list_records():
    return jsonify(
        [
            {"id": r.id, "charge_point_id": r.charge_point_id, "payload": r.payload}
            for r in MeterValueRepo().get_values(
                request.args.get("charge_point_ids", None),
                int(request.args.get("page", 1)),
                int(request.args.get("per_page", 10)),
            )
        ]
    )


@app.route("/detail/<int:record_id>", methods=["GET"])
def detail_record(record_id):
    record = MeterValueRepo().get_value(record_id)
    if record:
        return jsonify(
            {
                "id": record.id,
                "charge_point_id": record.charge_point_id,
                "payload": record.payload,
            }
        )
    else:
        return jsonify({"error": "Record not found"}), 404


if __name__ == "__main__":
    app.run(debug=True)
