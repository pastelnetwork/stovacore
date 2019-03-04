from django import forms


class ConsoleCommandForm(forms.Form):
    command = forms.CharField(label='command', max_length=100)


class SendCoinsForm(forms.Form):
    recipient_wallet = forms.CharField(label='Wallet Address', max_length=100)
    amount = forms.FloatField(label='amount')
    comment = forms.CharField(label='Comment', max_length=100)


class IdentityRegistrationForm(forms.Form):
    address = forms.CharField(label='address', min_length=26, max_length=35)


class ArtworkRegistrationForm(forms.Form):
    image_data = forms.FileField()
    # artist_name = forms.CharField(label='Artist', max_length=200)
    # artist_website = forms.CharField(label='Website', max_length=200)
    # artist_written_statement = forms.CharField(label='Written statement', max_length=200)
    # artwork_title = forms.CharField(label='Title', max_length=200)
    # artwork_series_name = forms.CharField(label='Series Name', max_length=200)
    # artwork_creation_video_youtube_url = forms.CharField(label='youtube video url', max_length=200)
    # artwork_keyword_set = forms.CharField(label='Keywords', max_length=200)
    # total_copies = forms.FloatField(label='Total Copies')


class TransferRegistrationForm(forms.Form):
    recipient_pubkey = forms.CharField(label='Recipient\'s public key', max_length=200)
    imagedata_hash = forms.CharField(label='Image hash', max_length=200)
    copies = forms.IntegerField(label='copies')


class TradeRegistrationForm(forms.Form):
    imagedata_hash = forms.CharField(label='Image hash', max_length=200)
    tradetype = forms.ChoiceField(label="Trade type", choices=(("bid", "bid"), ("ask", "ask")))
    copies = forms.IntegerField(label='copies')
    price = forms.IntegerField(label='price')
    expiration = forms.IntegerField(label='expiration')
