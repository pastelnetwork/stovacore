{% extends "views/base.tpl" %}

{% import "macros.tpl" as macros %}


{% block body %}
<div class="row">
    <div class="col-sm-3 mt-3">
            <h4>Receiving address:</h4>
            <p class="break-word">{{ receivingaddress }}</p>
    </div>

    <div class="col-sm-3 mt-3">
            <h4>Send coins:</h4>
            <p>Balance: {{ balance }}</p>
            <form method="post">
                <input type="hidden" name="csrfmiddlewaretoken" value="{{ csrf_token }}" />
                <table class="table">
                    {{ form }}
                </table>
                <button type="submit" class="btn btn-danger btn-center">Send</button>
            </form>
    </div>

    <div class="col-sm-3 mt-3">
        <h4>Collateral UTXOs:</h4>
        <table class="table">
            {% for txid in collateral_utxos %}
                <tr>
                    <td>{{ macros.render_transaction_link(txid) }}</td>
                </tr>
            {% endfor %}
        </table>
    </div>

    <div class="col-sm-12 mt-3">
        <h4>Unspent Transactions:</h4>
        <table class="table">
            <thead>
                <tr>
                    <th>txid</th>
                    <th>vout</th>
                    <th>generated</th>
                    <th>address</th>
                    <th>amount</th>
                    <th>confirmations</th>
                    <th>spendable</th>
                </tr>
            </thead>
            <tbody>
                {% for transaction in listunspent %}
                    <tr>
                        <td>{{ macros.render_transaction_link(transaction["txid"]) }}</td>
                        <td>{{ transaction["vout"] }}</td>
                        <td>{{ transaction["generated"] }}</td>
                        <td>{{ macros.render_address_link(transaction["address"]) }}</td>
                        <td>{{ transaction["amount"] }}</td>
                        <td>{{ transaction["confirmations"] }}</td>
                        <td>{{ transaction["spendable"] }}</td>
                    </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}
