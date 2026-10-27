
Terminoloji
================================================
Proje kapsamında kullanılan terimler aşağıda açıklanmıştır.

Pazaralanı
~~~~~~~~~~~~~
Çevrimiçi satış platformlarında satış yapmak isteyen şirketlerin, çevrimiçi mağazalar açarak
ürünlerini sunduğu ve kolayca büyük bir müşteri havuzuna ulaşabildiği sistemlerdir.

Akinon Commerce Cloud
~~~~~~~~~~~~~~~~~~~~~~~~
Akinon'un bulut çözümlerini içeren ve de müşterilerin ihtiyaçlarına uygun çözümleri
kendierinin de geliştirebildiği modüler bulut ortamıdır.

Omnitron
~~~~~~~~~~~~~~~~~~~~~
Akinon'un ürün envanterinde temel e-ticaret fonksiyonlarını oluşturan ve tüm satış kanalı
operasyonlarını yönetebildiği bir panel sunan üründür.

Channel App
~~~~~~~~~~~~~~~~
Yeni bir pazaralanı entegrasyonu için gereken temel yapıyı bulunduran ve farklı pazaralanları için
farklı ihtiyaçlar olabileceğinden dolayı esnek bir altyapı sunan projedir.

Channel App Template
~~~~~~~~~~~~~~~~~~~~~
Channel App'i bir bağımlılık olarak barındıran ve yeni pazaralanı entegrasyonu için doğrudan
klonlanarak ilerlenebilecek taslak projedir.

Celery
~~~~~~~~~~~~~~~
Asenkron olarak, belirli zamanlarda ve belirli aralıklarda task çalıştırma imkanı sunan , dağıtık kuyruk
yapısı ile taskları sıralı olarak işleyen ve yoğun kaynak gerektiren kuyruklar için de işçi sayısının
ayarlanabildiği teknolojidir.

Flower
~~~~~~~~~~~~
Flower, Celery için önyüz sağlayan bir yönetim aracıdır.

OperationalEvent
~~~~~~~~~~~~~~~~~
Omnitron üzerinde operasyonel süreçlerde oluşan olayları kayıt altına alan modeldir.
Her olay; bir seviye (``level``), olay tipi (``event_type``), kaynak (``source``), mesaj ve
isteğe bağlı bağlam (``context``), etiket (``tags``) ve ham veri (``raw_data``) alanlarından oluşur.
Channel App'ten gelen hata raporları, ``OperationalEventDto.from_error_report()`` metodu
aracılığıyla bu modele dönüştürülerek Omnitron'a iletilir.

EventType
~~~~~~~~~~
``OperationalEvent`` modelinde kaydedilen olayın hangi domain nesnesinden kaynaklandığını
belirten sabit değer tipidir. Channel App, işlenen nesnenin ``action_content_type`` değerine
göre otomatik olarak uygun bir ``event_type`` belirler:

- ``product_error``: Ürün akışlarındaki hatalar
- ``product_price_error``: Ürün fiyatı akışlarındaki hatalar
- ``product_stock_error``: Ürün stoğu akışlarındaki hatalar
- ``product_image_error``: Ürün görseli akışlarındaki hatalar
- ``order_error``: Sipariş akışlarındaki hatalar
- ``cancellation_request_error``: İptal talebi akışlarındaki hatalar
- ``category_error``: Kategori yapısı akışlarındaki hatalar
- ``batch_request_error``: Batch request işlem hataları
- ``attribute_value_error``: Öznitelik değeri hataları
- ``unknown_error``: Bilinmeyen veya eşleşmeyen diğer hatalar (fallback)

LogLevel
~~~~~~~~~
``OperationalEvent`` modelinde kaydedilen olayın önem seviyesini belirten sabit değer tipidir.
Olası değerler: ``debug``, ``info``, ``warning``, ``error``, ``critical``.
Channel App, başarılı işlemler için ``info``, başarısız işlemler için ``error`` seviyesini kullanır.
