import pytest
from PlanReview.guis.create_physics_manual_tab import (
    is_valid_automated_test,
    is_valid_manual_tab,
    create_key,
)
from PlanReview.utils.constants import (KEY_OUT_DOMAIN_NAME, KEY_OUT_DESC,
                                        KEY_OUT_COMMENT, FAILED_AUTOMATED_TEST,
                                        KEY_INPUT_TEXT)



@pytest.fixture
def mock_window():
    """
    Mock window for testing.
    Replace this with actual window mocking if needed.
    """
    return {
        create_key('Test1', 'Desc1', KEY_INPUT_TEXT): '',  # Add relevant keys and initial values
        create_key('Test2', 'Desc2', KEY_INPUT_TEXT): '',
        # Add other keys as needed
    }


def test_is_valid_automated_test(mock_window):
    # Test when all comments are 'Script Fail: Comment Needed'
    failed_tests = [
        {KEY_OUT_DOMAIN_NAME: 'Test1', KEY_OUT_DESC: 'Desc1', KEY_OUT_COMMENT: FAILED_AUTOMATED_TEST},
        {KEY_OUT_DOMAIN_NAME: 'Test2', KEY_OUT_DESC: 'Desc2', KEY_OUT_COMMENT: FAILED_AUTOMATED_TEST},
    ]
    assert is_valid_automated_test(mock_window, failed_tests) is False

    # Test when at least one comment is not 'Script Fail: Comment Needed'
    failed_tests[0][KEY_OUT_COMMENT] = 'User Comment'
    assert is_valid_automated_test(mock_window, failed_tests) is True

def test_is_valid_manual_tab(mock_window):
    # Test when all checkboxes are valid
    values = {
        create_key('Test1', 'Check1', 'RadioYes'): True,
        create_key('Test1', 'Check1', 'RadioNo'): False,
        create_key('Test1', 'Check1', 'RadioNA'): False,
        create_key('Test2', 'Check2', 'RadioYes'): True,
        create_key('Test2', 'Check2', 'RadioNo'): False,
        create_key('Test2', 'Check2', 'RadioNA'): True,
    }
    check_boxes = {
        'Test1': [{'KEY_OUT_TEST': 'Check1'}],
        'Test2': [{'KEY_OUT_TEST': 'Check2'}],
    }
    failed_tests = []

    assert is_valid_manual_tab(mock_window, values, check_boxes, failed_tests) is True

    # Test when at least one checkbox is not valid
    values[create_key('Test2', 'Check2', 'RadioNA')] = False
    assert is_valid_manual_tab(mock_window, values, check_boxes, failed_tests) is False
