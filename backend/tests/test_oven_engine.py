from app.services.oven_engine import (
    Interval,
    Occupancy,
    RecipeDurations,
    bake_span,
    build_occupancies,
    find_conflicts,
    is_valid_actual_bake_end,
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


def test_actual_bake_end_truncates_bake_keeps_ferment():
    recipe = RecipeDurations(20, 30)  # 发酵 [100,120) 烘烤 [120,150)
    ferment, bake = build_occupancies(1, 5, 100, recipe, actual_bake_end=135)
    assert ferment.interval == Interval(100, 120)
    assert bake.interval == Interval(120, 135)


def test_no_actual_bake_end_unchanged():
    recipe = RecipeDurations(20, 30)
    ferment, bake = build_occupancies(1, 5, 100, recipe)
    assert ferment.interval == Interval(100, 120)
    assert bake.interval == Interval(120, 150)


def test_actual_bake_end_validation_bounds():
    recipe = RecipeDurations(20, 30)  # 烘烤段 [120,150]
    assert bake_span(100, recipe) == Interval(120, 150)
    assert is_valid_actual_bake_end(100, recipe, 120)  # 烘烤起点
    assert is_valid_actual_bake_end(100, recipe, 150)  # 原烘烤结束
    assert is_valid_actual_bake_end(100, recipe, 135)
    assert not is_valid_actual_bake_end(100, recipe, 119)  # 早于烘烤起点
    assert not is_valid_actual_bake_end(100, recipe, 151)  # 晚于原烘烤结束


def test_truncated_tail_frees_window():
    recipe = RecipeDurations(20, 30)
    existing = [Occupancy(1, Interval(0, 100), "bake", 99)]  # 批次前的时段已被占满
    existing += build_occupancies(1, 5, 100, recipe, actual_bake_end=125)
    w = next_free_window(existing, 1, duration=30, search_from=0)
    assert w == Interval(125, 155)  # 截出的尾段计入可开工窗口
    untruncated = [Occupancy(1, Interval(0, 100), "bake", 99)] + build_occupancies(1, 5, 100, recipe)
    w2 = next_free_window(untruncated, 1, duration=30, search_from=0)
    assert w2 == Interval(150, 180)  # 未截断时只能从原烘烤结束后起算


def test_truncated_tail_not_a_conflict():
    recipe = RecipeDurations(20, 30)
    cand = build_occupancies(1, 6, 130, RecipeDurations(0, 10))  # 只落在被截掉的尾段
    existing = build_occupancies(1, 5, 100, recipe, actual_bake_end=125)
    assert find_conflicts(existing, cand) == []
    untruncated = build_occupancies(1, 5, 100, recipe)
    assert find_conflicts(untruncated, cand)  # 未截断时同一候选必冲突
