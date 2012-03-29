import templeton.handlers
#import templeton.logs
import templeton.middleware
import handlers
import web

templeton.middleware.patch_middleware()

urls = templeton.handlers.load_urls(handlers.urls)

app = web.application(urls, handlers.__dict__)


if __name__ == '__main__':
    #templeton.logs.setup_stream()
    try:
        handlers.init()
    except AttributeError:
        pass
    app.run()
