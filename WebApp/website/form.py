from django import forms


class AudioForm(forms.Form):
    audio = forms.FileField(label="Audio File")


