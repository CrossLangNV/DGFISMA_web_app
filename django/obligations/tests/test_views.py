from django.test import TestCase
from rest_framework.test import APIClient


from ..views import ReportingObligationSingleROHtmlAPIView
from ..models import ReportingObligation


class SingleRoViewTestCase(TestCase):
    def setUp(self):

        ro_str = "35 Liabilities issued by banks located outside the EU are not recognised as MREL- eligible . Eligible liabilities must be issued by an entity that is located within the EU , otherwise it is possible that resolution authorities ’ powers may not be applied . However , the 2018 MREL policy still recognises minority interests in subsidiaries ( i.e. own funds instruments issued to external investors ) as MREL - eligible to the extent that they are recognised in the own funds of the EU parent , if the foreign subsidiary is part of the resolution group of the EU parent ( i.e. the resolution strategy envisages that the foreign subsidiary would be resolved through the EU parent ) . 36 Banks are expected to tackle proactively the possible impact of Brexit . The SRB monitors the evolution of the stock and issuances of liabilities governed by UK law in the context of Brexit . Such liabilities are MREL - eligible based on the application of the current legal framework . However , the SRB will address on a case - by - case basis the possible effect of Brexit on the stock of MREL - eligible instruments ."
        self.doc_id = "df213a80-46b7-50ca-b439-c82f223d2317"
        self.ro = ReportingObligation.objects.create(
            rdf_id="test", name=ro_str, definition=ro_str, version="d16bba97890"
        )

    def test_view_url_exists_at_desired_location(self):
        client = APIClient()
        client.login(username="admin", password="admin")
        response = self.client.get("/obligations/api/ros")
        self.assertEqual(response.status_code, 200)

    def test_it_ro_view(self):

        client = APIClient()
        client.login(username="admin", password="admin")

        body = {"ro": self.ro.name, "doc_id": "df213a80-46b7-50ca-b439-c82f223d2317"}

        client.post("/obligations/api/ros/ro_html_view", body)

    def test_ro_view(self):
        view = ReportingObligationSingleROHtmlAPIView()

        class Request:
            data = {"ro": self.ro.name, "doc_id": self.doc_id}

        request = Request()

        view.post(
            request=request,
        )
