# -*- coding: utf-8 -*-
from meya import Component


class HelloWorld(Component):

    def start(self):
        # flush the content database
        content_list = self.db.table('content').filter()
        for content in content_list:
            self.db.table('content').delete(content["id"])
        return self.respond()
