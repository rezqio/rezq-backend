from unittest import mock

from rezq.utils.patch_model import patch_model


def test_patch_model():
    mock_model = mock.MagicMock()

    patch_model(
        mock_model, {
            'foo': 'bar',
        },
    )

    assert mock_model.foo == 'bar'

    mock_model.full_clean.assert_called_once()
    mock_model.save.assert_called_once()
