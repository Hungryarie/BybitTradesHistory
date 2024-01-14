import pytest
from app.db.utils import sort_stream
from app.errors import KeyTypeError


@pytest.mark.asyncio
async def test_sort_stream():
    """test the sorting of the stream output in ascending order
    and not in lexicographical order"""

    raw_data = [
        (b'1705072083140-0', {...}),
        (b'1705072083137-10', {...}),
        (b'1705072083137-11', {...}),
        (b'1705072083137-9', {...})
    ]
    expected_data = [
        (b'1705072083137-9', {...}),
        (b'1705072083137-10', {...}),
        (b'1705072083137-11', {...}),
        (b'1705072083140-0', {...}),
    ]
    sorted_data = await sort_stream(raw_data) 
    assert sorted_data == expected_data


@pytest.mark.asyncio
async def test_sort_stream_bytes():
    """test if the sort_string will accept bytes as sorting keys"""

    raw_data = [
        (b'1705072083173-0', {...}),
        (b'1705072083137-10', {...}),
    ]
    try:
        await sort_stream(raw_data)
    except Exception as e:
        assert False, f"byte data couldn't be sorted: {e}"

@pytest.mark.asyncio
async def test_sort_stream_string():
    """test if the sort_string will accept strings as sorting keys"""

    raw_data = [
        ('1705072083173-0', {...}),
        ('1705072083137-10', {...}),
    ]
    try:
        await sort_stream(raw_data)
    except Exception as e:
        assert False, f"string data couldn't be sorted: {e}"


@pytest.mark.asyncio
async def test_sort_stream_type_inconsistency():
    """test if the sort_string raises a TypeError when a 
    inconsistent list of types is passed"""

    raw_data = [
        (b'1705072083173-0', {...}),
        ('1705072083137-10', {...}),
    ]
    with pytest.raises(KeyTypeError):
        await sort_stream(raw_data)
    