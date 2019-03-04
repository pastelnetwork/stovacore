{% extends "views/base.tpl" %}

{% import "macros.tpl" as macros %}


{% block body %}
<div class="row">
    <div class="col-sm-12 mt-3">
        <h5>Form:</h5>
        <p>actticket_txid: {{ actticket_txid }}</p>
        <p>ticket: {{ final_actticket }}</p>
        <form method="post" enctype="multipart/form-data">
            <input type="hidden" name="csrfmiddlewaretoken" value="{{ csrf_token }}" />
            <table class="table">
                {{ form }}
            </table>
            <button type="submit" class="btn btn-danger btn-center">Register</button>
        </form>
    </div>
</div>
{% endblock %}
