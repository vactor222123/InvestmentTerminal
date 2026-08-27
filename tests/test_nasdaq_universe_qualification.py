from datetime import datetime,timezone
from investment_terminal.operations.nasdaq_universe_qualification import NasdaqUniverseQualificationService
NOW=datetime(2026,8,27,tzinfo=timezone.utc)
NASDAQ=("Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares\n"
        "AAA|Alpha|Q|N|N|100|N|N\nTEST|Test|Q|Y|N|100|N|N\nBAD|Bad|Q|N|D|100|N|N\nFile Creation Time: 0827202612:00|||||||\n").encode()
OTHER=("ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot Size|Test Issue|NASDAQ Symbol\n"
       "BRK.B|Berkshire|N|BRK.B|N|100|N|BRK.B\nSPY|SPDR|P|SPY|Y|100|N|SPY\nFile Creation Time: 0827202612:01|||||||\n").encode()
class Client:
    def __init__(self,data=None):self.data=data or {"NASDAQ_LISTED":NASDAQ,"OTHER_LISTED":OTHER}
    def fetch(self):return self.data
def test_qualifies_filters_projects_and_archives(tmp_path):
    private,report=NasdaqUniverseQualificationService(client=Client(),archive_directory=tmp_path,clock=lambda:NOW,minimum_accepted=1).qualify()
    assert [x["yahoo_symbol"] for x in private["members"]]==["AAA","BRK-B","SPY"]
    assert report["coverage"]=={"source_rows":5,"accepted":3,"etf":1,"non_etf":2,"excluded_test":1,"excluded_status":1,"projection_failure":0,"source_file_count":2,"unique_yahoo_symbol_count":3,"collision_count":0}
    assert len(list(tmp_path.glob("*.txt")))==2 and "AAA" not in str(report)
def test_invalid_tail_fails_after_exact_archive(tmp_path):
    data={"NASDAQ_LISTED":NASDAQ.replace(b"File Creation Time:",b"Missing:"),"OTHER_LISTED":OTHER}
    import pytest
    with pytest.raises(ValueError,match="creation time"):
        NasdaqUniverseQualificationService(client=Client(data),archive_directory=tmp_path,clock=lambda:NOW,minimum_accepted=1).qualify()
    assert len(list(tmp_path.glob("*.txt")))==1
def test_collision_fails_closed(tmp_path):
    other=OTHER.replace(b"BRK.B",b"AAA",1)
    import pytest
    with pytest.raises(ValueError,match="collisions"):
        NasdaqUniverseQualificationService(client=Client({"NASDAQ_LISTED":NASDAQ,"OTHER_LISTED":other}),archive_directory=tmp_path,clock=lambda:NOW,minimum_accepted=1).qualify()
