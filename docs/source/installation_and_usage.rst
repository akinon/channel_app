
Kurulum ve Kullanım
================================================

.. TODO buraya gerek olmayabilir çünkü bu dokümantasyon channel_app için olacak ve de doğrudan
    kullanılmayacak müşteri channel_app_template'i kopyalayacak ve içerisinde güncellemesi gereken
    akışları override edecek. (channel_app de requirements.txt dosyasında bulunacak ki güncellemeleri
    alabilsin) Bu durumda kurulum ve kullanım kılavuzu channel_app_template içerisinde olmalı sistemle ilgili genel
    bilgi ve akışların içeriği de bu dokümantasyonda bulunmalı.
    Ya da channel_app_template altındaki kurulum/kullanım kılavuzu burada yazılır oraya da kopyalanır



Lokalde kurulum ve taskların test edilmesi
_______________________________________________
Yazacağımız uygulama Omnitron'a bir Akinon Commerce Cloud (ACC) uygulaması olarak bağlanacak ve o uygulamaya
tanımlı kullanıcı bilgilerini kullanacak.
Lokalden test ettiğimiz senaryoda Omnitron kullanıcı bilgileri ile ACC uygulaması hazırlamadan
da test edebiliriz.
Geliştirmelerin hazır olduğunu düşündüğümüz noktada uygulamayı sunucu ortamında ayağa kaldırıp
orada da test edebiliriz.

Dokümantasyon Ubuntu tabanlı işletim sistemleri için hazırlanmıştır.

Adımlar
~~~~~~~~

* Öncelikle sistemdeki Python sürümünü kontrol edelim.
  3.8 ve üzeri sürümler Channel App Template projesi için yeterlidir.

.. code-block:: bash

    python --version
    python3 --version

    $: Python 3.8.10

* Eğer Python yüklü değilse ya da sürümünüz eskiyse Python kurulumunu apt komutlarıyla tamamlayabilirsiniz.
  Öncelikle `apt install` komutunu denemeniz tavsiye edilir.
  Versiyonu bulamaması durumunda add-apt-repository ile ilerleyip sonrasında tekrar `apt install` ile kurulumu yapabilirsiniz.
  Bu şekilde sisteminizdeki `apt` aradığınız pakete ulaşabiliyorsa yeni bir `ppa` eklemenize gerek kalmaz.

.. code-block:: bash

    sudo add-apt-repository ppa:deadsnakes/ppa
    sudo apt update -y
    sudo apt install python3.10

* `apt` komutlarıyla gerekli paketleri sisteme yüklüyoruz.
  Bunlar Python paket yönetici pip, versiyon kontrol aracı Git, task sunucusu Celery ve Celery'nin
  broker ihtiyacı için Redis'ten oluşuyor.

.. code-block:: bash

    sudo apt install python3-pip git redis-server python-celery-common
    pip3 install --upgrade pip


* Projeyi lokal sistemimize kopyalıyoruz.
  git klonlama işlemini terminalde aktif olan klasöre yapacağı için, komutu çalıştırmadan önce
  tercih ettiğiniz proje klasörüne `cd` ile geçmeniz önerilir.

.. code-block:: bash

    git clone git@bitbucket.org:akinonteam/channel_app_template.git

* Farklı projelerin bağımlıkları arasında çakışma olmaması adına virtual environment kullanmanız önerilir.
  Virtual environment aracı olarak virtualenvwrapper kullanabilirsiniz.
  Kurulum için pip ile yükleyebilirsiniz.

.. code-block:: bash

    pip3 install virtualenvwrapper
    which virtualenvwrapper.sh
    $: /home/osboxes/.local/bin/virtualenvwrapper.sh

* Sonrasında aşağıdaki satırları `.bashrc` dosyasının sonuna ekleyin. `source` komutuna vermeniz
  gereken dosya konumu kendi sisteminizdeki konum olması gerekiyor.
  Bu da yukarıda çalıştırdığımız `which` komutu çıktısını ifade ediyor.

    `gedit ~/.bashrc` ile dosyayı düzenleyebilirsiniz.

.. code-block:: bash

    export VIRTUALENVWRAPPER_PYTHON=/usr/bin/python3
    export WORKON_HOME=~/Envs
    source /home/osboxes/.local/bin/virtualenvwrapper.sh

* `source` komutundan sonra virtual environment kullanıma hazır oluyor.
  `mkvirtualenv` komutu ile yeni bir izole ortam oluşturabilirsiniz.
  Sonrasında `workon` komutu ile bir ortamı etkinleştirip `deactivate` ile kapatabilirsiniz.

.. code-block:: bash

    source ~/.bashrc
    mkvirtualenv channel
    workon channel

* Virtual environment aktifleştikten sonra pip ile proje için gerekli paketleri kurabilirsiniz.

.. code-block:: bash

    pip install -r requirements.txt

* Flower'ı çalıştırıyoruz. Öncesinde bazı ortam değişkenlerini `export` etmemiz gerekiyor.
  Her seferinde tek tek export yapmak yerine, bu değerleri `.env` dosyasına KEY=VALUE şeklinde kaydedip topluca
  export edecek komutu da çağırabilirsiniz.


.. code-block:: bash

    # Topluca export (öncesinde .env dosyasını oluşturmak gerekiyor)
    export $(grep -v '^#' .env | xargs)

    # Tek tek export
    export BROKER_HOST=127.0.0.1
    export BROKER_DATABASE_INDEX=4
    export BROKER_PORT=6379

    celery -A channel_app.celery_app flower --address=127.0.0.1 --port=8008


* Celery işçi processleri de çalıştıralım.
  Kullanıcı bilgileri ve bazı ortam değişkenleri sizin ortamınız için farklı değerlerde olacaktır.
  MAIN_APP_URL: Protokol bilgisi hariç Omnitron url'i
  OMNITRON_CHANNEL_ID: Uygulamanın bağlanacağı satış kanalı id değeri.
  OMNITRON_CATALOG_ID: Bağlı satış kanalının katalog id değeri.

.. code-block:: bash

    # Topluca export (öncesinde .env dosyasını oluşturmak gerekiyor)
    export $(grep -v '^#' .env | xargs)

    # Tek tek export
    export MAIN_APP_URL=localhost:8000
    export OMNITRON_USERNAME=admin
    export OMNITRON_PASSWORD=password
    export OMNITRON_CHANNEL_ID=1
    export OMNITRON_CATALOG_ID=1
    export BROKER_HOST=127.0.0.1
    export BROKER_PORT=6379
    export BROKER_DATABASE_INDEX=4

    celery -A channel_app.celery_app worker -l info

* Redis sunucusu varsayılan olarak kurulum sonrası özellikle kapatılmadıkça ayakta oluyor.
  Ping komutuyla test edip `redis-server` ile kaldırabilirsiniz.

.. code-block:: bash

    redis-cli ping
    redis-server

* Sistem için gerekli her şey hazır. Son olarak bir taskı tetikleyerek kurulumları tamamlıyoruz.

.. code-block:: bash

    curl --request POST \
    --url http://localhost:8008/api/task/apply/channel_app.app.setup.tasks.create_or_update_category_tree_and_nodes


Sunucu ortamına versiyon çıkma
__________________________________
Lokalde testler tamamlanıp taskların hazır olduğu düşünüldüğünde, geliştirmeleri sunucu ortamına
gönderip orada da çalıştırıp test etmek sağlıklı olacaktır.

Aşağıdaki dokümandaki adımları izleyerek ACC üzerinde `project` ve `application` tanımlamanız
gerekmektedir. Bu adımları aynı uygulama için daha önce takip ettiyseniz kodun ve etiketlerin
gönderildiği noktaya geçebilirsiniz.

Bu adımlardan sonra SSH açık anahtarını sisteme yüklemeniz gerekiyor.
Eğer daha önce oluşturmadıysanız `ssh-keygen` komutu ile oluşturabilirsiniz.

.. code-block:: bash

    ssh-keygen

    Generating public/private rsa key pair.
    Enter file in which to save the key (/home/osboxes/.ssh/id_rsa):
    Enter passphrase (empty for no passphrase):
    Enter same passphrase again:
    Your identification has been saved in /home/osboxes/.ssh/id_rsa
    Your public key has been saved in /home/osboxes/.ssh/id_rsa.pub
    The key fingerprint is:
    SHA256:25c2hMf7PWJVTNAYznE6bbyPqZal8Gzc9EjunbbIt3A osboxes@osboxes
    The key's randomart image is:
    +---[RSA 3072]----+
    |              +=.|
    |             o.*o|
    |              =o+|
    |           o   o+|
    |        S . +  ..|
    |         o.o o++.|
    |        . .=*X+E.|
    |           oX*B*o|
    |           oo+*+*|
    +----[SHA256]-----+

* Sonrasında da açık anahtar değerini aşağıdaki komutla terminale yazdırıp kopyalayarak
  Akinon Commerce Cloud üzerindeki alana yapıştırabilirsiniz.

.. code-block:: bash

    cat ~/.ssh/id_rsa.pub
    $: ssh-rsa <PUBLIC_KEY> osboxes@osboxes

* Akinon Commerce Cloud üzerine uygulama versiyonlarını çıkabilmek için son hazırlık adımı olarak
  `My Applications` altından alakalı uygulamayı bulun ve URL alanını kopyalayın.
  `git remote add` komutundaki url bölümüne yapıştırıp komutu çalıştırın.

.. code-block:: bash

    git remote add my_application <REPOSITORY_URL>

* Geliştirmeleri git süreçlerinden geçirip derleme ve ayağa kaldırma adımlarını
  ACC arayüzüne bırakıyoruz.

.. code-block:: bash

    git commit -am "Initial commit"
    git push
    git tag v001
    git push my_application v001

* Son adım olarak da ACC üzerinde uygulamamıza tıklayıp Build butonuna bastığımızda v001 versiyonunu derleyebiliriz.
  Derleme tamamlandığında uygulamayı seçip `Deploy Selected Projects` derlenmiş versiyonu ayağa kaldırabiliriz.


Komutların üzerine yazılması
_______________________________
ChannelIntegration kısmındaki geliştirmeler API ile ilgili bilgiler önceden bilinemeyeceği için örnek veri
ile çalışır durumda.
Akışların tamamlanması için ChannelIntegration altındaki komutların miras alınarak `send`
metotlarının ezilmesi gerekmektedir.

.. code-block:: python

    from channel_app.channel.commands.products import SendInsertedProducts as BaseSendInsertedProducts
    class SendInsertedProducts(BaseSendInsertedProducts):
        def send(self, validated_data):
            # implement new send block here
            pass

Yeni sınıfın oluşturulması doğrudan kullanılacağı anlamına gelmiyor bunun için `ChannelIntegration`
sınıfında `actions` parametresi üzerinde tanımlama yapmak gerekiyor.
Burada dikkat edilmesi gereken nokta `BaseIntegration` sınıfında verilen anahtar parametrenin aynısı
ile tanımlanması gerekmektedir. Aksi takdirde `tasks.py` akışında değişiklik yapmadan çalışmayacaktır.

.. code-block:: python

    from channel_app.channel.integration import ChannelIntegration as BaseIntegration
    from channel.commands.products import SendInsertedProducts
    class ChannelIntegration(BaseIntegration):
        actions = {
        ...
        "send_inserted_products": SendInsertedProducts,
        ...
        }

Eğer Omnitron tarafındaki komutlarda da değişiklik gereken bir yapı oluştuysa oradaki komutların da
miras alınarak değişen metotların ezilmesi gerekiyor.
Burada yukarıda anlatılan adımlar `OmnitronIntegration` için uygulanmalı.
Yapı tamamen aynı.
Burada tek farklı olan nokta sınıf isimleri, bu sebeple aynı adımları uygulayabilirsiniz.


Yukarıdaki adımlardan bağımsız olarak akış üzerinde bazı komutların kaldırılması ya da
yeni komutların eklenmesi gerekiyorsa tasks.py üzerinde değişiklik yapmak şart olacaktır.
Örnek bir task akışı aşağıdaki gibidir. İhtiyaca göre `do_action` komutlarını ekleyip çıkartabilirsiniz.

Komutların ne tarz bir girdi beklediğini ve çıktı verdiğini `run` metotlarındaki tip bilgisine bakarak
kontrol edebilirsiniz.

Komutları Celery üzerinden tetiklemek için hazırladığınız metodu `@app.task` ile sarmanız gerekmektedir.

Eğer metodun testleri sonrası her şeyin tamam olduğunu düşünüyorsanız, bir çalışma programı
belirleyerek `celery_schedule_conf.py` dosyasında tanımlayabilirsiniz.

.. code-block:: python

    @app.task
    def insert_products():
        with OmnitronIntegration(content_type=ContentType.product.value) as omnitron_integration:
            products = omnitron_integration.do_action(key='get_inserted_products')
            products = omnitron_integration.do_action(key='get_mapped_products', objects=products)
            products = omnitron_integration.do_action(key='get_product_stocks', objects=products)
            products = omnitron_integration.do_action(key='get_product_prices', objects=products)
            products = omnitron_integration.do_action(key='get_product_images', objects=products)
            products = omnitron_integration.do_action(key='get_product_categories', objects=products)
            if products:
                ChannelIntegration().do_action(key='send_inserted_products',
                                               objects=products,
                                               batch_request=omnitron_integration.batch_request)

