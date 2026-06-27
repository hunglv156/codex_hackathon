from unittest.mock import Mock, patch

from src.sink.clickhouse_sink import ClickHouseSink


def build_sink(mock_client):
    with patch("src.sink.clickhouse_sink.clickhouse_connect.get_client", return_value=mock_client):
        return ClickHouseSink("localhost", 9000, "aiops", "default", "")


def test_sink_retry_on_failure():
    mock_client = Mock()
    mock_client.insert.side_effect = RuntimeError("down")
    sink = build_sink(mock_client)
    rows = [{"service_name": "svc", "value": 1.0}]
    with patch("src.sink.clickhouse_sink.time.sleep"):
        assert sink.insert_batch("metrics", rows) is False
    assert mock_client.insert.call_count == 3


def test_sink_batch_not_single_row():
    mock_client = Mock()
    sink = build_sink(mock_client)
    rows = [{"service_name": "svc", "value": float(index)} for index in range(50)]
    assert sink.insert_batch("metrics", rows) is True
    mock_client.insert.assert_called_once()
    args, kwargs = mock_client.insert.call_args
    assert len(args[1]) == 50
