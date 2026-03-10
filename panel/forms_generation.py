from django import forms
from .models_generation import VideoGenerationJob, ImageGenerationJob


class VideoGenerationForm(forms.ModelForm):
    source_asset_id = forms.IntegerField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = VideoGenerationJob
        fields = ["source_image", "prompt", "seconds", "quality", "aspect_ratio"]
        widgets = {
            "prompt": forms.Textarea(attrs={"rows": 4, "class": "mz-inp"}),
            "seconds": forms.NumberInput(attrs={"min": 2, "max": 12, "class": "mz-inp"}),
            "quality": forms.Select(attrs={"class": "mz-sel"}),
            "aspect_ratio": forms.Select(attrs={"class": "mz-sel"}),
            "source_image": forms.ClearableFileInput(attrs={"accept": "image/*", "class": "mz-inp"}),
        }


class ImageGenerationForm(forms.ModelForm):
    source_asset_1_id = forms.IntegerField(required=False, widget=forms.HiddenInput())
    source_asset_2_id = forms.IntegerField(required=False, widget=forms.HiddenInput())
    source_asset_3_id = forms.IntegerField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = ImageGenerationJob
        fields = ["source_image_1", "source_image_2", "source_image_3", "prompt", "quality"]
        widgets = {
            "prompt": forms.Textarea(attrs={"rows": 4, "class": "mz-inp"}),
            "quality": forms.Select(attrs={"class": "mz-sel"}),
            "source_image_1": forms.ClearableFileInput(attrs={"accept": "image/*", "class": "mz-inp"}),
            "source_image_2": forms.ClearableFileInput(attrs={"accept": "image/*", "class": "mz-inp"}),
            "source_image_3": forms.ClearableFileInput(attrs={"accept": "image/*", "class": "mz-inp"}),
        }