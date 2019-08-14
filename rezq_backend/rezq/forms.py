from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth.forms import UserCreationForm
from rezq.models.user import User


class RezqUserCreationForm(UserCreationForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True

    class Meta:
        model = User
        fields = ('email',)


class RezqUserChangeForm(UserChangeForm):

    class Meta:
        model = User
        fields = '__all__'
