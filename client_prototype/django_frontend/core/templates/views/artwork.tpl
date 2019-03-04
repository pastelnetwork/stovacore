{% extends "views/base.tpl" %}

{% import "macros.tpl" as macros %}


{% block body %}
<div class="row">
    <div class="col-sm-12">
        <h3><a href="/artwork/{{ artid }}">Share url</a></h3>
        {{ function }}
    </div>

    <div class="col-sm-2 mt-3">
        <h3>Owners</h3>
        <table class="table table-striped">
            <tr>
                <td>
                    <img width="169" height="240" src="/chunk/{{ art_ticket["thumbnailhash"].hex() }}" />
                </td>
            </tr>
            <tr>
                <td>
                    <a href="/download/{{ artid }}">Download</a>
                </td>
            </tr>
            {% for owner, copies in art_owners.items() %}
                <tr>
                    <td>
                        <abbr title="{{ owner.hex() }}">owner: {{ owner.hex()|truncate(17) }}</abbr><br />
                        copies: {{ copies }}
                    </td>
                </tr>
            {% endfor %}
        </table>
    </div>

    <div class="col-sm-8 mt-3">
        <ul class="nav nav-tabs" id="myTab" role="tablist">
            <li class="nav-item">
                <a class="nav-link active" id="home-tab" data-toggle="tab" href="#mytrades" role="tab" aria-controls="mytrades" aria-selected="true">My trades</a>
            </li>
            <li class="nav-item">
                <a class="nav-link" data-toggle="tab" href="#opentickets" role="tab" aria-controls="opentickets" aria-selected="false">Open Tickets</a>
            </li>
            <li class="nav-item">
                <a class="nav-link" data-toggle="tab" href="#closedtickets" role="tab" aria-controls="closedtickets" aria-selected="false">Closed Tickets</a>
            </li>
            <li class="nav-item">
                <a class="nav-link" data-toggle="tab" href="#newtrade" role="tab" aria-controls="newtrade" aria-selected="false">New Trade</a>
            </li>
        </ul>

        <div class="tab-content" id="myTabContent">
            <div class="tab-pane fade show active" id="mytrades" role="tabpanel" aria-labelledby="mytrades-tab">
                <div class="row">
                    {% for created, txid, valid, status, tickettype, ticket in my_trades %}
                        <div class="col-sm-3 mx-2 my-2 bg-light border border-primary">
                            {{ macros.render_trade(created, txid, valid, status, tickettype, ticket, pubkey, csrf_token) }}
                        </div>
                    {% endfor %}
                </div>
            </div>


            <div class="tab-pane fade" id="opentickets" role="tabpanel" aria-labelledby="opentickets-tab">
                <div class="row">
                    {% for created, txid, valid, status, tickettype, ticket in open_tickets %}
                        <div class="col-sm-3 mx-2 my-2 bg-light border border-primary">
                            {{ macros.render_trade(created, txid, valid, status, tickettype, ticket, pubkey, csrf_token) }}
                        </div>
                    {% endfor %}
                </div>
            </div>

            <div class="tab-pane fade" id="closedtickets" role="tabpanel" aria-labelledby="closedtickets-tab">
                <div class="row">
                    {% for created, txid, valid, status, tickettype, ticket in closed_tickets %}
                        <div class="col-sm-3 mx-2 my-2 bg-light border border-primary">
                            {{ macros.render_trade(created, txid, valid, status, tickettype, ticket, pubkey, csrf_token) }}
                        </div>
                    {% endfor %}
                </div>
            </div>

            <div class="tab-pane fade" id="newtrade" role="tabpanel" aria-labelledby="newtrade-tab">
                <div class="row">
                    <div class="col-sm-6 mt-3">
                        <h2>Transfer</h2>
                        <form method="post" action="/artwork/{{ artid }}?function=transfer">
                            <input type="hidden" name="csrfmiddlewaretoken" value="{{ csrf_token }}" />
                            <table class="table">
                                {{ transferform }}
                            </table>
                            <button type="submit" class="btn btn-success btn-center">Transfer artwork</button>
                        </form>
                    </div>

                    <div class="col-sm-6 mt-3">
                        <h2>Trade</h2>
                        <form method="post" action="/artwork/{{ artid }}?function=trade">
                            <input type="hidden" name="csrfmiddlewaretoken" value="{{ csrf_token }}" />
                            <table class="table">
                                {{ tradeform }}
                            </table>
                            <button type="submit" class="btn btn-success btn-center">Trade artwork</button>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
