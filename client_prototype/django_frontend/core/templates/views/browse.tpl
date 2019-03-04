{% extends "views/base.tpl" %}

{% import "macros.tpl" as macros %}


{% block body %}
<div class="row">
    <div class="col-sm-12 mt-3">
        <h3>Browse</h3>
        <ul class="nav nav-tabs" id="myTab" role="tablist">
            <li class="nav-item">
                <a class="nav-link active" id="home-tab" data-toggle="tab" href="#art" role="tab" aria-controls="art" aria-selected="true">Art</a>
            </li>
            <li class="nav-item">
                <a class="nav-link" id="profile-tab" data-toggle="tab" href="#tickets" role="tab" aria-controls="tickets" aria-selected="false">Tickets</a>
              </li>
        </ul>

        <div class="tab-content" id="myTabContent">
            <div class="tab-pane fade show active" id="art" role="tabpanel" aria-labelledby="art-tab">
                <table class="table">
                    {% for artid, regticket in artworks %}
                        <tr>
                            <td>
                                Artist: {{ regticket["artist_name"] }}<br />
                                Artwork: {{ regticket["artwork_title"] }}<br />
                                Keywords: {{ regticket["artwork_keyword_set"] }}<br />
                                Copies: {{ regticket["total_copies"] }}<br />
                                <img width="169" height="240" src="/chunk/{{ regticket["thumbnailhash"].hex() }}" />
                            </td>
                            <td>
                                <a href="/artwork/{{ artid.hex() }}">{{ artid.hex() }}</a>
                            </td>
                        </tr>
                    {% endfor %}
                </table>
            </div>

            <div class="tab-pane fade" id="tickets" role="tabpanel" aria-labelledby="tickets-tab">
                {% if txid == "" %}
                    <table class="table">
                        <thead>
                            <tr>
                                <th>TXID</th>
                                <th>Type</th>
                                <th>Ticket</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for txid, tickettype, ticket in tickets %}
                            <tr>
                                <td><a href="/browse/{{ txid }}">{{ txid }}</a></td>
                                {% if tickettype == "identity" %}
                                    <td>ID</td>
                                    <td>
                                        blockchain_address: {{ ticket["ticket"]["blockchain_address"] }}<br />
                                        public_key: {{ ticket["ticket"]["public_key"] }}<br />
                                    </td>
                                {% elif tickettype == "regticket" %}
                                    <td>Registration</td>
                                    <td>
                                        {% set artid = ticket['ticket']['imagedata_hash'].hex() %}
                                        artist_name: {{ ticket["ticket"]["artist_name"] }}<br />
                                        artwork_title: {{ ticket["ticket"]["artwork_title"] }}<br />
                                        imagedata_hash: <a href="/artwork/{{ artid }}">{{ artid }}</a><br />
                                    </td>
                                {% elif tickettype == "actticket" %}
                                    <td>Activation</td>
                                    <td>
                                        author: {{ ticket["ticket"]["author"] }}<br />
                                        registration_ticket_txid: {{ ticket["ticket"]["registration_ticket_txid"] }}<br />
                                    </td>
                                {% elif tickettype == "transticket" %}
                                    <td>Transfer</td>
                                    <td>
                                        {% set artid = ticket['ticket']['imagedata_hash'].hex() %}
                                        image: <a href="/artwork/{{ artid }}">{{ artid }}</a><br />
                                        copies: {{ ticket["ticket"]["copies"] }}<br />
                                        public_key: {{ ticket["ticket"]["public_key"] }}<br />
                                        recipient: {{ ticket["ticket"]["recipient"] }}<br />
                                    </td>
                                {% elif tickettype == "tradeticket" %}
                                    <td>Trade</td>
                                    <td>
                                        {% set artid = ticket['ticket']['imagedata_hash'].hex() %}
                                        type: {{ ticket["ticket"]["type"] }}<br />
                                        image: <a href="/artwork/{{ artid }}">{{ artid }}</a><br />
                                        copies: {{ ticket["ticket"]["copies"] }}<br />
                                        price: {{ ticket["ticket"]["price"] }}<br />
                                        expiration: {{ ticket["ticket"]["expiration"] }}<br />
                                    </td>
                                {% else %}
                                    <td>UNKOWN TYPE: {{ tickettype }}</td>
                                    <td>{{ ticket|pprint }}</td>
                                {% endif %}
                            </tr>
                        </tbody>
                        {% endfor %}
                    </table>
                {% else %}
                    <h5>ticket:</h5>
                    <p>{{ ticket|pprint }}</p>
                {% endif %}
                </div>
        </div>
    </div>
</div>
{% endblock %}
