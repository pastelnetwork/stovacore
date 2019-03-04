import io
from PIL import Image

from django.conf import settings
from django.shortcuts import render, redirect, Http404, HttpResponse

from core.models import client
from core.forms import IdentityRegistrationForm, SendCoinsForm, ArtworkRegistrationForm, ConsoleCommandForm, \
    TransferRegistrationForm, TradeRegistrationForm


def index(request):
    infos = client.call("get_info")

    return render(request, "views/index.tpl", {"infos": infos,
                                               "pastel_basedir": settings.PASTEL_BASEDIR})


def tasks(request):
    tasks = client.call("list_background_tasks")

    return render(request, "views/tasks.tpl", {"tasks": tasks})


def walletinfo(request):
    listunspent, receivingaddress, balance, collateral_utxos = client.call("get_wallet_info", client.pubkey)

    form = SendCoinsForm()
    if request.method == "POST":
        form = SendCoinsForm(request.POST)
        if form.is_valid():
            address = form.cleaned_data["recipient_wallet"]
            amount = form.cleaned_data["amount"]
            comment = form.cleaned_data["comment"]

            ret = client.call("send_to_address", address, amount, comment)

            if ret is not None:
                form.add_error(None, ret)
            else:
                return redirect("/walletinfo/")

    return render(request, "views/walletinfo.tpl", {"listunspent": listunspent, "receivingaddress": receivingaddress,
                                                    "balance": balance, "form": form,
                                                    "collateral_utxos": collateral_utxos})


def identity(request):
    ret = client.call("get_identities")
    addresses, all_identities, identity_txid, identity_ticket = ret

    form = IdentityRegistrationForm()
    if request.method == "POST":
        form = IdentityRegistrationForm(request.POST)
        if form.is_valid():
            address = form.cleaned_data["address"]
            if address not in addresses:
                form.add_error(None, "Addess does not belong to us!")
            else:
                client.call("register_identity", address)
                return redirect("/identity")

    return render(request, "views/identity.tpl", {"addresses": addresses,
                                                  "identity_txid": identity_txid,
                                                  "identity_ticket": identity_ticket, "form": form,
                                                  "all_identities": all_identities})


def portfolio(request):
    my_artworks = client.call("get_artworks_owned_by_me")
    return render(request, "views/portfolio.tpl", {"my_artworks": my_artworks,
                                                   "pubkey": client.pubkey})


def artwork(request, artid_hex):
    transferform, tradeform = None, None

    function = request.GET.get("function")
    if request.method == "POST":
        if function == "transfer":
            transferform = TransferRegistrationForm(request.POST)
            if transferform.is_valid():
                recipient_pubkey = transferform.cleaned_data["recipient_pubkey"]
                imagedata_hash = transferform.cleaned_data["imagedata_hash"]
                copies = transferform.cleaned_data["copies"]
                client.call("register_transfer_ticket", recipient_pubkey, imagedata_hash, copies)
                return redirect('artwork', artid_hex=artid_hex)
        elif function == "trade":
            tradeform = TradeRegistrationForm(request.POST)
            if tradeform.is_valid():
                imagedata_hash = tradeform.cleaned_data["imagedata_hash"]
                tradetype = tradeform.cleaned_data["tradetype"]
                copies = tradeform.cleaned_data["copies"]
                price = tradeform.cleaned_data["price"]
                expiration = tradeform.cleaned_data["expiration"]
                client.call("register_trade_ticket", imagedata_hash, tradetype, copies, price, expiration)
                return redirect('/tasks', artid_hex=artid_hex)
        else:
            return HttpResponse("Invalid function")

    if transferform is None:
        if artid_hex is not "":
            transferform = TransferRegistrationForm(initial={"imagedata_hash": artid_hex})
        else:
            transferform = TransferRegistrationForm()

    if tradeform is None:
        if artid_hex is not "":
            tradeform = TradeRegistrationForm(initial={"imagedata_hash": artid_hex})
        else:
            tradeform = TradeRegistrationForm()

    art_ticket, art_owners, open_tickets, closed_tickets = client.call("get_artwork_info", artid_hex)
    my_trades = client.call("get_my_trades_for_artwork", artid_hex)

    return render(request, "views/artwork.tpl", {"function": function,
                                                 "art_ticket": art_ticket,
                                                 "art_owners": art_owners,
                                                 "open_tickets": open_tickets,
                                                 "closed_tickets": closed_tickets,
                                                 "transferform": transferform, "tradeform": tradeform,
                                                 "artid": artid_hex,
                                                 "pubkey": client.pubkey,
                                                 "my_trades": my_trades})


def exchange(request):
    results = client.call("ping_masternodes")
    return render(request, "views/exchange.tpl", {"results": results})


def trending(request):
    resp = "TODO"
    return render(request, "views/trending.tpl", {"resp": resp})


def browse(request, txid=""):
    artworks, tickets, ticket = client.call("browse", txid)
    tickets.reverse()
    return render(request, "views/browse.tpl", {"artworks": artworks, "tickets": tickets, "txid": txid, "ticket": ticket})


def register(request):
    form = ArtworkRegistrationForm()

    final_actticket, actticket_txid = None, None

    if request.method == "POST":
        form = ArtworkRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            # get the actual image data from the form field
            image_field = form.cleaned_data["image_data"]

            # convert image
            converted_image = io.BytesIO()
            tmp = Image.open(image_field)
            tmp.save(converted_image, format="png")

            image_data = converted_image.getvalue()
            image_name = image_field.name

            actticket_txid, final_actticket = client.call("register_image", image_name, image_data)

    return render(request, "views/register.tpl", {"form": form, "actticket_txid": actticket_txid,
                                                  "final_actticket": final_actticket})


def console(request):
    form = ConsoleCommandForm()
    output = ""
    if request.method == "POST":
        form = ConsoleCommandForm(request.POST)
        if form.is_valid():
            command = form.cleaned_data["command"].split(" ")

            error, result = client.call("execute_console_command", *command)
            output = result

    return render(request, "views/console.tpl", {"form": form, "output": output})


def explorer(request, functionality, id=""):
    if functionality == "chaininfo":
        chaininfo = client.call("explorer_get_chaininfo")
        return render(request, "views/explorer_chaininfo.tpl", {"chaininfo": chaininfo})
    elif functionality == "block":
        blockcount, block = client.call("explorer_get_block", id)

        if id == "":
            return redirect("/explorer/block/%s" % blockcount)

        if block is None:
            raise Http404("Block does not exist")

        # we need a paginator min and max
        if type(id) == str:
            blocknum = int(block["height"])
        else:
            blocknum = int(id)

        pages = (max(0, blocknum-5), min(blocknum+5+1, blockcount+1))
        return render(request, "views/explorer_block.tpl", {"block": block,
                                                            "blocknum": blocknum,
                                                            "pages": pages,
                                                            "blockcount": blockcount})
    elif functionality == "transaction":
        transaction = client.call("explorer_gettransaction", id)
        if transaction is None:
            raise Http404("Address does not exist")
        return render(request, "views/explorer_transaction.tpl", {"transaction": transaction})
    elif functionality == "address":
        transactions = client.call("explorer_getaddresses", id)
        if transactions is None:
            raise Http404("Address does not exist")
        return render(request, "views/explorer_addresses.tpl", {"id": id, "transactions": transactions})
    else:
        return redirect("/")


def chunk(request, chunkid_hex):
    image_data = client.call("get_chunk", chunkid_hex)

    if image_data is None:
        raise Http404

    # TODO: set content type properly
    return HttpResponse(image_data, content_type="image/png")


def download(request, artid):
    image = client.call("download_image", artid)
    return HttpResponse(image, content_type="image/png")
