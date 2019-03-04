{% extends "views/base.tpl" %}

{% import "macros.tpl" as macros %}


{% block body %}
<div class="row">
    <div class="col-sm-12 mx-auto">
        {% if id != "" %}
            <h3>Address: {{ id }}</h3>
        {% endif %}
        <table class="table table-striped">
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
                {% for transaction in transactions %}
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
        {#<table class="table table-striped">
            <tbody>
                <tr>
                    <td>amount</td>
                    <td>{{ transaction['amount'] }}</td>
                <tr>
                    <td>blockhash</td>
                    <td>{{ macros.render_blockchain_link(transaction["blockhash"]) }}</td>
                </tr>
                <tr>
                    <td>blockindex</td>
                    <td>{{ macros.render_blockchain_link(transaction["blockindex"]) }}</td>
                </tr>
                <tr>
                    <td>blocktime</td>
                    <td>{{ transaction['blocktime'] }}</td>
                </tr>
                <tr>
                    <td>confirmations</td>
                    <td>{{ transaction['confirmations'] }}</td>
                </tr>
                <tr>
                    <td>details</td>
                    <td>
                        {% for detail in transaction['details'] %}
                            <table class="table">
                                <tr>
                                    <td>account</td>
                                    <td>{{ detail['account'] }}</td>
                                </tr>
                                <tr>
                                    <td>address</td>
                                    <td>{{ macros.render_address_link(detail['address']) }}</td>
                                </tr>
                                <tr>
                                    <td>category</td>
                                    <td>{{ detail['category'] }}</td>
                                </tr>
                                <tr>
                                    <td>amount</td>
                                    <td>{{ detail['amount'] }}</td>
                                </tr>
                                <tr>
                                    <td>vout</td>
                                    <td>{{ detail['vout'] }}</td>
                                </tr>
                                <tr>
                                    <td>size</td>
                                    <td>{{ detail['size'] }}</td>
                                </tr>
                            </table>
                        {% endfor %}
                    </td>
                </tr>
                <tr>
                    <td>generated</td>
                    <td>{{ transaction['generated'] }}</td>
                </tr>
                <tr>
                    <td>time</td>
                    <td>{{ transaction['time'] }}</td>
                </tr>
                <tr>
                    <td>timereceived</td>
                    <td>{{ transaction['timereceived'] }}</td>
                </tr>
                <tr>
                    <td>txid</td>
                    <td>{{ macros.render_transaction_link(transaction["txid"]) }}</td>
                </tr>
                <tr>
                    <td>vjoinsplit</td>
                    <td>{{ transaction['vjoinsplit'] }}</td>
                </tr>
                <tr>
                    <td>walletconflicts</td>
                    <td>{{ transaction['walletconflicts'] }}</td>
                </tr>
            </tbody>

        </table>#}
    </div>
</div>
{% endblock %}
