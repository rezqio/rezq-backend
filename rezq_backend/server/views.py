from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.http import HttpResponseBadRequest
from django.http import HttpResponseNotFound
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie
from rezq.models.dev import MockS3File


def _get_mock_s3_file_or_error_response(request):
    if 'key' in request.GET:
        key = request.GET['key']
    else:
        try:
            key = request.POST['key']
        except KeyError:
            return HttpResponseBadRequest("Missing parameter 'key'")

    try:
        return MockS3File.objects.get(id=key)
    except MockS3File.DoesNotExist:
        return HttpResponseNotFound(f'File UUID does not exist: {key}')
    except ValidationError as e:
        if 'UUID' in str(e):
            return HttpResponseBadRequest(f'Invalid UUID: {key}')


class MockS3View(View):

    def get(self, request):
        mock_s3_file = _get_mock_s3_file_or_error_response(request)

        if isinstance(mock_s3_file, HttpResponse):
            # There's a problem; either 400 or 404
            return mock_s3_file

        filename = mock_s3_file.file.name.split('/')[-1]

        try:
            response = HttpResponse(
                mock_s3_file.file,
                content_type='application/pdf',
            )
        except ValueError:
            return HttpResponseBadRequest('No file associated')
        except FileNotFoundError:
            return HttpResponseBadRequest(
                'File associated, but not on filesystem',
            )

        response['Content-Disposition'] = f'attachment; filename={filename}'

        return response

    def post(self, request):
        mock_s3_file = _get_mock_s3_file_or_error_response(request)

        if isinstance(mock_s3_file, HttpResponse):
            # There's a problem; either 400 or 404
            return mock_s3_file

        try:
            mock_s3_file.file = request.FILES['file']
        except KeyError:
            return HttpResponseBadRequest('Missing file in POST request')

        mock_s3_file.full_clean()
        mock_s3_file.save()

        return HttpResponse(status=201)


@ensure_csrf_cookie
def CsrfView(_):
    return HttpResponse()
