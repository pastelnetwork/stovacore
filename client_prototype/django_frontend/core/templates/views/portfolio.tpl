{% extends "views/base.tpl" %}

{% import "macros.tpl" as macros %}


{% block body %}
<div class="row">
    <div class="col-sm-12">
        <p>My pubkey: {{ pubkey.hex() }}</p>
    </div>


    <div class="col-sm-12 mt-3">
        <p>My artworks</p>
        <table class="table table-striped">
            {% for artid, copies in my_artworks %}
                <tr>
                    <td>
                        artwork: <a href="/artwork/{{ artid.hex() }}">{{ artid.hex() }}</a><br />
                        {{ copies }}
                    </td>
                </tr>
            {% endfor %}
        </table>
    </div>
</div>
{% endblock %}
