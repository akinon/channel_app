.. Channel App Template documentation master file, created by
   sphinx-quickstart on Fri Mar 11 16:36:02 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Channel App Template Proje Dokümantasyonu
================================================
Channel App Template projesi, Akinon Commerce Cloud (ACC) üzerinde farklı pazaralanlarına yapılacak
entegrasyonlar için taslak oluşturmak amacıyla hazırlanmıştır.
Bu proje öncesinde, müşteriler Omnitron'da entegrasyonu Akinon tarafından yapılan pazaralanlarında
satış yapabiliyordu.
Sistemde, Akinon tarafından entegrasyonu yapılmamış olan pazaralanları için geliştirme yapabileceği
bir ortam da sunulmuyordu.
Channel App Template projesi ile birlikte yeterli teknik uzmanlığa sahip şirketler, istedikleri
pazaralanlarına entegrasyon yapabilirler.

Bunun için projeyi klonlayıp (ya da bir bağımlılık olarak projeye tanımlayarak), gerekli bağlantı
kodlarını yazarak, ürün, stok, fiyat gibi akışlarda hedef pazaralanına özgü özelleştirmeleri de yapmaları
yeterlidir.
Bu adımlardan sonra, yeni uygulama ACC üzerinde kurulup ayağa kaldırıldığında,
Omnitron'da önceden entegrasyonu yapılmış bulunan pazaralanlarını kullanabildikleri
gibi kullanır hale gelebilirler.

--------------------------------
Teknolojiler ve Kütüphaneler
--------------------------------
1. Python 3.8
2. Celery 5
3. Flower
4. Sentry

İçerik
=============================================

.. toctree::
   :maxdepth: 3

   installation_and_usage
   architecture
   flows
   command_reference
   terminology
