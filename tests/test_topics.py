from truthbrush_oil_study.topics import classify_post_topic


def test_classify_post_topic_handles_energy_and_geo_keywords():
    assert classify_post_topic("drill baby drill and lower gas prices") == "energy_policy"
    assert classify_post_topic("Iran sanctions now") == "geopolitics"
