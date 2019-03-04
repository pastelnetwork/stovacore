{% extends "views/base.tpl" %}

{% import "macros.tpl" as macros %}


{% block body %}
<div class="row">
    <div class="col-sm-3 mt-3">
            <h4>ALL Pastel Identities</h4>
            {% for txid, ticket in all_identities %}
                <table class="table">
                    <tr>
                        <td>Blockchain address:</td>
                        <td>{{ txid }}</td>
                        <td>{{ ticket.ticket.public_key }}</td>
                    </tr>
                </table>
            {% endfor %}

            <h4>My Pastel Identities</h4>
            {% for address in addresses %}
                <table class="table">
                    <tr>
                        <td>Blockchain address:</td>
                        <td>{{ address }}</td>
                    </tr>
                </table>
            {% endfor %}

            {% if identity_ticket == none %}
                Your identity is not yet established!
            {% else %}
                Your identity is established, but you can add another one:
                <form method="post">
                    <input type="hidden" name="csrfmiddlewaretoken" value="{{ csrf_token }}" />
                    <table class="table">
                        {{ form }}
                    </table>
                    <button type="submit" class="btn btn-success btn-center">Establish identity</button>
                </form>
            {% endif %}
            txid: {{ identity_txid }}
            ticket: {{ identity_ticket|pprint }}
    </div>
</div>
{% endblock %}
