# test_db.py (run from project root)
from dotenv import load_dotenv
load_dotenv()

from access_analysis import db


def main():
    # Test insert
    ok = db.insert_log(
        user_id="test_user",
        access_risk=0.1,
        final_risk=0.1,
        decision="ALLOW",
        reason="connection test",
        request_type="test",
        response_status="200",
        input_hash="abc123",
    )
    print("Insert OK:", ok)

    # Test fetch
    avg = db.fetch_historical_avg("test_user")
    print("Historical avg:", avg)

    logs = db.fetch_recent_logs("test_user", limit=5)
    print("Recent logs:", logs)


if __name__ == "__main__":
    main()