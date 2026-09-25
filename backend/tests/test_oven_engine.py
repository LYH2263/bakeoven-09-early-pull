from app.services.oven_engine import (
    Interval,
    Occupancy,
    RecipeDurations,
    build_occupancies,
    find_conflicts,
    is_within_bake,
    next_free_window,
)


def test_half_open_no_touch_conflict():
    a = Occupancy(1, Interval(0, 30), "bake", 1)
    b = Occupancy(1, Interval(30, 60), "bake", 2)
    assert find_conflicts([a], [b]) == []


def test_overlap_detected():
    recipe = RecipeDurations(20, 30)
    cand = build_occupancies(1, 9, 10, recipe)
    existing = [Occupancy(1, Interval(25, 40), "bake", 1)]
    assert find_conflicts(existing, cand)


def test_next_free_window_after_busy():
    existing = [
        Occupancy(1, Interval(0, 40), "ferment", 1),
        Occupancy(1, Interval(40, 70), "bake", 1),
    ]
    w = next_free_window(existing, 1, duration=30, search_from=0)
    assert w == Interval(70, 100)


def test_next_free_in_gap():
    existing = [
        Occupancy(1, Interval(0, 20), "bake", 1),
        Occupancy(1, Interval(80, 100), "bake", 2),
    ]
    w = next_free_window(existing, 1, duration=30, search_from=0)
    assert w == Interval(20, 50)


def test_actual_out_truncates_bake_only():
    # start 0, ferment [0,40), bake [40,75)；实际出炉 60
    recipe = RecipeDurations(40, 35)
    ferment, bake = build_occupancies(1, 1, 0, recipe, actual_out_min=60)
    assert ferment.interval == Interval(0, 40)  # 发酵段起止不动
    assert bake.interval == Interval(40, 60)  # 烘烤段以实际出炉为终点


def test_unregistered_batch_unchanged():
    recipe = RecipeDurations(40, 35)
    assert build_occupancies(1, 1, 0, recipe, None) == build_occupancies(1, 1, 0, recipe)


def test_actual_out_equal_original_end_no_change():
    recipe = RecipeDurations(40, 35)
    ferment, bake = build_occupancies(1, 1, 0, recipe, actual_out_min=75)
    assert ferment.interval == Interval(0, 40)
    assert bake.interval == Interval(40, 75)


def test_is_within_bake_bounds():
    recipe = RecipeDurations(40, 35)  # bake [40,75]（闭区间校验）
    assert not is_within_bake(39, 0, recipe)  # 早于烘烤起点
    assert is_within_bake(40, 0, recipe)  # 等于烘烤起点
    assert is_within_bake(60, 0, recipe)
    assert is_within_bake(75, 0, recipe)  # 等于原烘烤结束
    assert not is_within_bake(76, 0, recipe)  # 晚于原烘烤结束


def test_truncated_tail_no_longer_conflicts():
    # 原烘烤 [40,75)，实际出炉 60；候选批次占 [60,90)
    recipe = RecipeDurations(40, 35)
    truncated = build_occupancies(1, 1, 0, recipe, actual_out_min=60)
    cand = [Occupancy(1, Interval(60, 90), "bake", 2)]
    assert find_conflicts(truncated, cand) == []
    # 未截断时同一候选仍冲突
    full = build_occupancies(1, 1, 0, recipe)
    assert find_conflicts(full, cand)


def test_window_counts_freed_tail():
    # 原烘烤 [40,75) 截到 60，炉在 60 起空；可排 15 分钟的活
    recipe = RecipeDurations(40, 35)
    existing = build_occupancies(1, 1, 0, recipe, actual_out_min=60)
    w = next_free_window(existing, 1, duration=15, search_from=0)
    assert w == Interval(60, 75)
    # 未截断时同样的活要等到 75
    full = build_occupancies(1, 1, 0, recipe)
    assert next_free_window(full, 1, duration=15, search_from=0) == Interval(75, 90)
