{% macro render_blockchain_link(id) %}
    <a href="/explorer/block/{{ id }}">{{ id }}</a>
{% endmacro %}

{% macro render_transaction_link(id, truncate=False) %}
    {% if truncate %}
        <a href="/explorer/transaction/{{ id }}">{{ id|truncate(10) }}</a><br />
    {% else %}
        <a href="/explorer/transaction/{{ id }}">{{ id }}</a><br />
    {% endif %}
{% endmacro %}

{% macro render_address_link(id, truncate=False) %}
    {% if truncate %}
        <a href="/explorer/address/{{ id }}">{{ id|truncate(10) }}</a><br />
    {% else %}
        <a href="/explorer/address/{{ id }}">{{ id }}</a><br />
    {% endif %}
{% endmacro %}

{% macro render_trade(created, txid, valid, status, tickettype, ticket, pubkey, csrf_token) %}
    <table class="table">
        <tr>
            <td>status</td>
            {% if status == "open" %}
                <td class="bg-success">OPEN</td>
            {% elif status == "locked" %}
                <td class="bg-warning">LOCKED</td>
            {% elif status == "done" %}
                <td class="bg-info">DONE</td>
            {% elif status == "invalid" %}
                <td class="bg-danger">INVALID</td>
            {% else %}
                <td class="bg-danger">BAD VALUE: {{ status }}</td>
            {% endif %}
        </tr>
        <tr>
            <td>type</td>
            <td>{{ ticket["type"] }}</td>
        </tr>
        <tr>
            <td>copies</td>
            <td>{{ ticket["copies"] }}</td>
        </tr>
        <tr>
            <td>price</td>
            <td>{{ ticket["price"] }}</td>
        </tr>
        <tr>
            <td>expiration</td>
            <td>{{ ticket["expiration"] }}</td>
        </tr>
        <tr>
            <td>created</td>
            <td>{{ created }}</td>
        </tr>
        <tr>
            <td>txid</td>
            <td><a href="/browse/{{ txid }}">{{ txid|truncate(10) }}</a></td>
        </tr>
        <tr>
            <td>user</td>
            <td><abbr title="{{ ticket["public_key"].hex() }}">{{ ticket["public_key"].hex()|truncate(10) }}</abbr></td>
        </tr>
        <tr>
            <td>watched_address</td>
            <td><abbr title="{{ ticket["watched_address"] }}">{{ render_address_link(ticket["watched_address"], truncate=True) }}</abbr></td>
        </tr>
        <tr>
            <td>collateral_txid</td>
            <td><abbr title="{{ ticket["collateral_txid"] }}">{{ render_transaction_link(ticket["collateral_txid"], truncate=True) }}</abbr></td>
        </tr>
        <tr>
            <td>Action:</td>
            <td>
                {% if status == "open" %}
                    <form method="post" action="/artwork/{{ ticket["imagedata_hash"].hex() }}?function=trade">
                        <input type="hidden" name="csrfmiddlewaretoken" value="{{ csrf_token }}" />

                        <input type="hidden" name="imagedata_hash" value="{{ ticket["imagedata_hash"].hex() }}" />
                        {% if ticket["type"] == "ask" %}
                            <input type="hidden" name="tradetype" value="bid" />
                        {% else %}
                            <input type="hidden" name="tradetype" value="ask" />
                        {% endif %}
                        <input type="hidden" name="copies" value="{{ ticket["copies"] }}" />
                        <input type="hidden" name="price" value="{{ ticket["price"] }}" />
                        <input type="hidden" name="expiration" value="0" />

                        {% if pubkey != ticket["public_key"] %}
                            <button type="submit" class="btn btn-success btn-center">
                            {% if ticket["type"] == "ask" %}
                                Buy
                            {% else %}
                                Sell
                            {% endif %}
                            </button>
                        {% endif %}
                    </form>
                {% endif %}
            </td>
        </tr>
    </table>
{% endmacro %}
