{% extends "views/base.tpl" %}

{% import "macros.tpl" as macros %}


{% block body %}
<div class="row">
    <div class="col-sm-12 mx-auto">
        <h3>Total blocks: {{ blocknum }} / {{ blockcount }}</h3>
        <table class="table table-striped">
            <tbody>
                <tr>
                    <td>anchor</td>
                    <td>{{ block["anchor"] }}</td>
                </tr>
                <tr>
                    <td>bits</td>
                    <td>{{ block["bits"] }}</td>
                </tr>
                <tr>
                    <td>chainwork</td>
                    <td>{{ block["chainwork"] }}</td>
                </tr>
                <tr>
                    <td>confirmations</td>
                    <td>{{ block["confirmations"] }}</td>
                </tr>
                <tr>
                    <td>difficulty</td>
                    <td>{{ block["difficulty"] }}</td>
                </tr>
                <tr>
                    <td>hash</td>
                    <td>{{ block["hash"] }}</td>
                </tr>
                <tr>
                    <td>height</td>
                    <td>{{ macros.render_blockchain_link(block["height"]) }}</td>
                </tr>
                <tr>
                    <td>merkleroot</td>
                    <td>{{ block["merkleroot"] }}</td>
                </tr>
                <tr>
                    <td>nonce</td>
                    <td>{{ block["nonce"] }}</td>
                </tr>
                <tr>
                    <td>previousblockhash</td>
                    <td>{{ macros.render_blockchain_link(block["previousblockhash"]) }}</td>
                </tr>
                <tr>
                    <td>nextblockhash</td>
                    <td>{{ macros.render_blockchain_link(block["nextblockhash"]) }}</td>
                </tr>
                <tr>
                    <td>size</td>
                    <td>{{ block["size"] }}</td>
                </tr>
                <tr>
                    <td>solution</td>
                    <td>{{ block["solution"] }}</td>
                </tr>
                <tr>
                    <td>time</td>
                    <td>{{ block["time"] }}</td>
                </tr>
                <tr>
                    <td>tx</td>
                    <td>
                        {% for transaction in block["tx"] %}
                            {{ macros.render_transaction_link(transaction) }}
                        {% endfor %}
                    </td>
                </tr>
                <tr>
                    <td>valuePools</td>
                    <td>{{ block["valuePools"] }}</td>
                </tr>
                <tr>
                    <td>version</td>
                    <td>{{ block["version"] }}</td>
                </tr>
            </tbody>
        </table>
    </div>
</div>

<div class="row">
    <div class="col-sm-12">
        <nav aria-label="Pagination">
            <ul class="pagination justify-content-center">
                <li class="page-item"><a class="page-link" href="/explorer/block/0">First</a></li>
                {% if pages[0] > 0 %}
                    <li class="page-item disabled"><a class="page-link">...</a></li>
                {% endif %}
                {% for i in range(pages[0], pages[1]) %}
                    {% if i == blocknum %}
                        <li class="page-item active"><a class="page-link" href="/explorer/block/{{ i }}">{{ i }}</a></li>
                    {% else %}
                        <li class="page-item"><a class="page-link" href="/explorer/block/{{ i }}">{{ i }}</a></li>
                    {% endif %}
                {% endfor %}
                {% if pages[1] <= blockcount %}
                    <li class="page-item disabled"><a class="page-link">...</a></li>
                {% endif %}
                <li class="page-item"><a class="page-link" href="/explorer/block/{{ blockcount }}">Last</a></li>
            </ul>

            <p class="text-center">Block {{ blocknum }} of {{ blockcount }}</p>
        </nav>
    </div>
</div>
{% endblock %}
