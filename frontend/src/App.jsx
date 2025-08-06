import { useState, useEffect, useRef } from 'react';
import { Sparkles, BarChart, ArrowRightCircle, Sun, Moon, PlusCircle, Pencil, Trash2 } from 'lucide-react';

// Başlangıç mesajı için bir sabit oluşturuldu.
const initialBotMessage = {
  id: 'bot-initial',
  sender: 'bot',
  text: 'Merhaba! İhracat yapmak istediğiniz ürün veya sektör adını (ör: "Zeytinyağı", "Mobilya", "Tekstil") girerek size en uygun ülkeleri önerebilirim.',
};

export default function App() {
  const [messages, setMessages] = useState([initialBotMessage]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [chatHistory, setChatHistory] = useState([]);
  const [activeChatId, setActiveChatId] = useState('chat-1');
  const [chatIdCounter, setChatIdCounter] = useState(2);
  const [currentChatTitle, setCurrentChatTitle] = useState('Yeni Sohbet');
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [editingChatId, setEditingChatId] = useState(null); // Sol paneldeki başlık düzenleme için yeni state
  const messagesEndRef = useRef(null);
  const titleInputRef = useRef(null);

  // Google Fonts'u uygulamaya dahil etmek için
  useEffect(() => {
    const link = document.createElement('link');
    link.href = 'https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600&display=swap';
    link.rel = 'stylesheet';
    document.head.appendChild(link);
    return () => {
      document.head.removeChild(link);
    };
  }, []);

  // Mesajlar güncellendiğinde en son mesaja otomatik olarak kaydırma yapar.
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Tema değişikliğinde body arka planını günceller.
  useEffect(() => {
    document.body.className = isDarkMode ? 'bg-gray-950' : 'bg-gray-50';
  }, [isDarkMode]);

  // Dark/Light modu arasında geçiş yapar.
  const toggleDarkMode = () => {
    setIsDarkMode(!isDarkMode);
  };

  // Yeni sohbet başlatma işlevi.
  const handleNewChat = () => {
    // Mevcut sohbeti geçmişe kaydet
    if (messages.length > 1) {
      const existingChat = {
        id: activeChatId,
        title: currentChatTitle,
        messages: messages,
      };
      setChatHistory((prevHistory) => {
        // Eğer sohbet zaten varsa, güncelle. Yoksa yeni olarak ekle.
        const chatExists = prevHistory.some(chat => chat.id === activeChatId);
        if (chatExists) {
          return prevHistory.map(chat => chat.id === activeChatId ? existingChat : chat);
        } else {
          return [existingChat, ...prevHistory];
        }
      });
    }

    setMessages([initialBotMessage]);
    setActiveChatId(`chat-${chatIdCounter}`);
    setCurrentChatTitle('Yeni Sohbet');
    setChatIdCounter((prevCounter) => prevCounter + 1);
  };

  // Sohbet başlığını düzenleme işlevi
  const handleTitleEdit = (e) => {
    setCurrentChatTitle(e.target.value);
  };

  // Geçmişten sohbet yükleme işlevi
  const handleLoadChat = (chatId) => {
    // Mevcut sohbeti geçmişe kaydetmeden önce kontrol et
    if (messages.length > 1) {
      const existingChat = {
        id: activeChatId,
        title: currentChatTitle,
        messages: messages,
      };
      setChatHistory((prevHistory) => {
        const chatExists = prevHistory.some(chat => chat.id === activeChatId);
        if (chatExists) {
          return prevHistory.map(chat => chat.id === activeChatId ? existingChat : chat);
        } else {
          return [existingChat, ...prevHistory];
        }
      });
    }

    const chatToLoad = chatHistory.find(chat => chat.id === chatId);
    if (chatToLoad) {
      setMessages(chatToLoad.messages);
      setActiveChatId(chatId);
      setCurrentChatTitle(chatToLoad.title);
      // Yüklenen sohbeti geçmişten çıkarıp en üste taşıyabiliriz.
      setChatHistory((prevHistory) => [chatToLoad, ...prevHistory.filter(chat => chat.id !== chatId)]);
    }
  };

  // Sol paneldeki sohbet adını düzenleme işlevi
  const handleLeftPanelTitleEdit = (chatId, newTitle) => {
    setChatHistory(prevHistory => prevHistory.map(chat =>
      chat.id === chatId ? { ...chat, title: newTitle } : chat
    ));
    if (activeChatId === chatId) {
      setCurrentChatTitle(newTitle);
    }
  };

  // Sohbet geçmişinden bir sohbeti silme işlevi
  const handleDeleteChat = (chatIdToDelete) => {
    setChatHistory((prevHistory) => prevHistory.filter(chat => chat.id !== chatIdToDelete));
    if (activeChatId === chatIdToDelete) {
      handleNewChat();
    }
  };

  // Modelden gelecek örnek yanıt için yapılandırılmış bir veri döndürür.
  const getDummyResponse = (product) => {
    const lowerCaseProduct = product.toLowerCase();

    // Simüle edilmiş veri bilimi modelinden alınmış yanıtlar
    const responses = {
      'zeytinyağı': {
        recommendation: `"Zeytinyağı" için en uygun potansiyel barındıran ülkeler:`,
        hsCodeInfo: `NLP analizi sonucunda ürününüz için en olası HS Kodu: 1509.`,
        countries: [
          { name: 'Germany', volume: 150000000, reason: 'Yüksek talep ve Türkiye\'den düşük rekabet.' },
          { name: 'France', volume: 120000000, reason: 'Büyük pazar ve güçlü ticaret ilişkileri.' },
          { name: 'Japan', volume: 90000000, reason: 'Yüksek kaliteye verilen önem ve artan talep.' },
        ],
        reason: `Önerilen ülkeler, yüksek ithalat hacmine sahip olmalarına rağmen, sizin gibi yeni bir ihracatçı için düşük rekabet avantajı sunmaktadır.`,
      },
      'güneş paneli': {
        recommendation: `"Güneş Paneli" için en uygun potansiyel barındıran ülkeler:`,
        hsCodeInfo: `NLP analizi sonucunda ürününüz için en olası HS Kodu: 8541.40.`,
        countries: [
          { name: 'United States of America', volume: 3000000000, reason: 'Yenilenebilir enerji yatırımları ve teşvikler.' },
          { name: 'Australia', volume: 1500000000, reason: 'Yüksek güneşlenme süresi ve evsel talep.' },
          { name: 'Brazil', volume: 800000000, reason: 'Devlet destekleri ve gelişmekte olan pazar.' },
        ],
        reason: `Bu ülkeler, yenilenebilir enerjiye olan küresel talebin hızla artması nedeniyle yüksek büyüme potansiyeline sahiptir.`,
      },
      'tekstil': {
        recommendation: `"Tekstil Sektörü" için en uygun potansiyel barındıran ülkeler:`,
        hsCodeInfo: `Sektör geniş olduğu için birden fazla HS Kodu olabilir.`,
        countries: [
          { name: 'Spain', volume: 2000000000, reason: 'Hızlı moda endüstrisi ve güçlü perakende pazarı.' },
          { name: 'United Kingdom', volume: 1800000000, reason: 'Marka sadakati ve e-ticaretin yaygınlığı.' },
          { name: 'Netherlands', volume: 1000000000, reason: 'Tekstil ticaretinde önemli bir merkez konumu.' },
        ],
        reason: `Bu ülkelerde Türk tekstil ürünlerine karşı yüksek talep ve olumlu algı bulunmaktadır.`,
      }
    };

    const dummyResponse = responses[lowerCaseProduct] || {
      recommendation: `"${product}" için en çok potansiyel barındıran ülkeler:`,
      hsCodeInfo: `NLP analizi devam ediyor...`,
      countries: [
        { name: 'Germany', volume: 150000000, reason: 'Yüksek talep ve az yerel üretim.' },
        { name: 'France', volume: 120000000, reason: 'Büyük pazar ve güçlü ticaret ilişkileri.' },
        { name: 'Sweden', volume: 80000000, reason: 'Yüksek büyüme potansiyeli ve yenilikçi pazar.' },
      ],
      reason: `Önerdiğimiz ülkeler, yüksek ithalat hacmine sahip olmalarına rağmen, sizin gibi yeni bir ihracatçı için düşük rekabet avantajı sunmaktadır.`,
    };

    // `chartData`'yı her zaman `countries` dizisinden oluşturur.
    dummyResponse.chartData = dummyResponse.countries.map(c => ({
      country: c.name,
      volume: c.volume / 1000000, // Milyon olarak
    }));

    return dummyResponse;
  };

  // Mesaj gönderme işlevini yönetir. (GÜNCELLENMİŞ HALİ)
  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: input,
    };
    
    // Önce kullanıcı mesajını ekrana ekle
    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    
    // Input'u temizle ve yükleniyor durumunu başlat
    const currentInput = input;
    setInput('');
    setIsLoading(true);

    // İlk kullanıcı mesajından sonra sohbet adını otomatik olarak belirle
    if (messages.length === 1) {
      setCurrentChatTitle(`${userMessage.text} Analizi`);
    }

    try {
      // --- BURASI GERÇEK API İSTEĞİNİN YAPILDIĞI YER ---
      const response = await fetch('http://127.0.0.1:5000/chat', { // Backend sunucunun adresi
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: currentInput }), // Backend'in beklediği format { "message": "..." }
      });

      if (!response.ok) {
        // Eğer sunucudan 4xx veya 5xx gibi bir hata kodu dönerse
        throw new Error(`API hatası: ${response.status} ${response.statusText}`);
      }

      const data = await response.json(); // Backend'den gelen JSON yanıtını al

      // Backend'den gelen yanıtı mesajlara ekle
      const botResponse = {
        id: `bot-${Date.now()}`,
        sender: 'bot',
        text: data.response, // Backend'in `jsonify({"response": response.text})` şeklinde döndürdüğü veri
      };
      
      setMessages((prevMessages) => [...prevMessages, botResponse]);

    } catch (error) {
      // Eğer ağ hatası veya fetch içinde bir sorun olursa
      console.error('Mesaj gönderilirken bir hata oluştu:', error);
      const errorResponse = {
        id: `bot-error-${Date.now()}`,
        sender: 'bot',
        text: `Üzgünüm, bir hata oluştu: ${error.message}. Lütfen backend sunucunun çalıştığından emin ol.`,
      };
      setMessages((prevMessages) => [...prevMessages, errorResponse]);
    } finally {
      // İstek başarılı da olsa, hata da olsa yükleniyor durumunu bitir
      setIsLoading(false);
    }
  };

  // Botun zengin yanıtını görselleştiren bileşen
  const renderRichResponse = (response) => {
    const recommendedCountryNames = response.countries.map(c => c.name);
    const userCountry = "Turkey";

    return (
      <div className={`flex flex-col p-4 rounded-lg shadow-md space-y-4 transition-colors duration-300 ${isDarkMode ? 'bg-gray-700 text-gray-200' : 'bg-white text-gray-800'}`}>
        <h4 className="flex items-center text-base font-bold text-indigo-400">
          <Sparkles className="w-4 h-4 mr-2 text-yellow-300" />
          {response.recommendation}
        </h4>
        <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>{response.reason}</p>

        {/* Harita görselleştirme */}
        {response.countries && response.countries.length > 0 && (
          <div className="space-y-2">
            <h5 className={`flex items-center font-semibold text-sm ${isDarkMode ? 'text-gray-200' : 'text-gray-800'}`}>
              <Sparkles className="w-4 h-4 mr-2 text-indigo-500" />
              Potansiyel Bölgeler
            </h5>
            {/* Inline SVG World Map */}
            <svg
              className="w-full h-auto rounded-lg shadow-md"
              viewBox="0 0 1000 500"
              xmlns="http://www.w3.org/2000/svg"
              style={{
                backgroundColor: isDarkMode ? '#1F2937' : '#E5E7EB',
              }}
            >
              {/* Default colors for all countries */}
              <g
                fill={isDarkMode ? '#4B5563' : '#D1D5DB'}
                stroke="#FFF"
                strokeWidth="0.5"
                strokeLinejoin="round"
              >
                {/* Simplified SVG Paths for a few countries and a placeholder for the rest of the world */}
                <path id="Germany" d="M480 200 L490 205 L495 200 L480 190 Z" />
                <path id="France" d="M450 200 L460 210 L470 205 L465 195 Z" />
                <path id="Japan" d="M900 250 L910 260 L920 255 L915 245 Z" />
                <path id="United States of America" d="M100 200 L150 220 L160 210 L110 190 Z" />
                <path id="Australia" d="M800 400 L820 410 L830 400 L810 390 Z" />
                <path id="Brazil" d="M300 350 L320 360 L330 350 L310 340 Z" />
                <path id="Spain" d="M420 220 L430 230 L440 225 L435 215 Z" />
                <path id="United Kingdom" d="M440 180 L450 185 L460 180 L455 175 Z" />
                <path id="Netherlands" d="M480 185 L485 190 L490 185 L485 180 Z" />
                <path id="Sweden" d="M520 160 L530 170 L540 165 L535 155 Z" />
                <path id="Turkey" d="M550 220 L560 225 L570 220 L565 215 Z" />

                {/* Rest of the world (placeholder) */}
                <path d="M0 0 H1000 V500 H0 Z" fill={isDarkMode ? '#4B5563' : '#E5E7EB'} />
              </g>

              {/* Apply custom colors for recommended countries and user's country */}
              {recommendedCountryNames.map((countryName) => (
                <path
                  key={countryName}
                  id={countryName}
                  d="" // Path data needs to be provided for each country. This is a simplified example.
                  fill={isDarkMode ? '#34D399' : '#10B981'}
                  stroke="#FFF"
                  strokeWidth="0.5"
                />
              ))}

              <path
                id="Turkey"
                d="M550 220 L560 225 L570 220 L565 215 Z" // Placeholder path for Turkey
                fill="#F97316"
                stroke="#FFF"
                strokeWidth="0.5"
              />
            </svg>
            <p className={`text-center text-xs mt-1 ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              (Harita, önerilen ülkeleri temsil eden basit bir görseldir.)
            </p>
          </div>
        )}

        <div className="grid md:grid-cols-2 gap-4">
          {/* Ülkeler listesi */}
          {response.countries && response.countries.length > 0 && (
            <div className="flex flex-col space-y-2">
              <h5 className={`font-semibold text-sm ${isDarkMode ? 'text-gray-200' : 'text-gray-800'}`}>Önerilen Ülkeler:</h5>
              <ul className="list-disc list-inside space-y-1 ml-4 text-sm">
                {response.countries.map((country, index) => (
                  <li key={index} className={`font-medium ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                    <span className="flex items-center">
                      <ArrowRightCircle className="w-4 h-4 mr-2 text-indigo-500" />
                      {country.name} - <span className={`font-normal ml-1 text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>{country.volume / 1000000} Milyon $</span>
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Tablo görünümü */}
          {response.countries && response.countries.length > 0 && (
            <div className="space-y-2">
              <h5 className={`flex items-center font-semibold text-sm ${isDarkMode ? 'text-gray-200' : 'text-gray-800'}`}>
                <BarChart className="w-4 h-4 mr-2 text-pink-500" />
                Detaylı İthalat Verileri
              </h5>
              <div className={`overflow-x-auto rounded-lg shadow-sm ${isDarkMode ? 'bg-gray-800' : 'bg-gray-100'}`}>
                <table className="min-w-full divide-y divide-gray-200 table-auto">
                  <thead className={isDarkMode ? 'bg-gray-700' : 'bg-gray-200'}>
                    <tr>
                      <th scope="col" className={`px-4 py-2 text-left text-xs font-medium uppercase tracking-wider ${isDarkMode ? 'text-gray-300' : 'text-gray-500'}`}>
                        Ülke
                      </th>
                      <th scope="col" className={`px-4 py-2 text-left text-xs font-medium uppercase tracking-wider ${isDarkMode ? 'text-gray-300' : 'text-gray-500'}`}>
                        Hacim (Milyon $)
                      </th>
                    </tr>
                  </thead>
                  <tbody className={`divide-y divide-gray-200 ${isDarkMode ? 'bg-gray-800 text-gray-300' : 'bg-white text-gray-700'}`}>
                    {response.countries.map((country, index) => (
                      <tr key={index}>
                        <td className="px-4 py-2 whitespace-nowrap text-xs font-medium">
                          {country.name}
                        </td>
                        <td className="px-4 py-2 whitespace-nowrap text-xs">
                          {country.volume / 1000000}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        {/* HS Kodu Tahmini */}
        <div className="flex items-center space-x-2 p-2 bg-indigo-500 bg-opacity-10 rounded-lg">
          <Sparkles className="w-3 h-3 text-indigo-500" />
          <span className={`text-xs font-semibold ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>{response.hsCodeInfo}</span>
        </div>
      </div>
    );
  };

  return (
    // Boşluğu eklemek için ana kapsayıcıya "py-8" (üst ve alt dolgu) eklendi.
    <div className={`flex flex-col min-h-screen py-8 antialiased transition-colors duration-300 ${isDarkMode ? 'bg-gray-950' : 'bg-gray-50'}`}>
      <div className={`flex flex-col md:flex-row flex-grow w-full max-w-4xl mx-auto shadow-xl rounded-2xl overflow-hidden transition-colors duration-300 ${isDarkMode ? 'bg-gray-900' : 'bg-white'}`}>

        {/* Sohbet Geçmişi Sütunu */}
        <div className={`hidden md:flex flex-col w-1/4 p-4 border-r transition-colors duration-300 ${isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-gray-100 border-gray-200'}`}>
          <div className="flex justify-between items-center mb-4">
            <h3 className={`text-lg font-semibold ${isDarkMode ? 'text-gray-200' : 'text-gray-800'}`}>Sohbetler</h3>
            <button
              onClick={handleNewChat}
              className={`p-2 rounded-full transition-colors duration-300 ${isDarkMode ? 'text-blue-400 hover:bg-gray-700' : 'text-blue-600 hover:bg-gray-200'}`}
              title="Yeni Sohbet Başlat"
            >
              <PlusCircle className="w-5 h-5" />
            </button>
          </div>
          <div className="flex-grow overflow-y-auto space-y-2">
            {chatHistory.map((chat) => (
              <div
                key={chat.id}
                onClick={() => {
                  if (editingChatId !== chat.id) {
                    handleLoadChat(chat.id);
                  }
                }}
                className={`flex items-center justify-between p-3 rounded-lg cursor-pointer transition-colors duration-200 group ${
                  activeChatId === chat.id
                    ? (isDarkMode ? 'bg-blue-600 text-white' : 'bg-blue-500 text-white')
                    : (isDarkMode ? 'hover:bg-gray-700 text-gray-300' : 'hover:bg-gray-200 text-gray-700')
                }`}
              >
                {editingChatId === chat.id ? (
                  <input
                    ref={titleInputRef}
                    type="text"
                    value={chat.title}
                    onChange={(e) => handleLeftPanelTitleEdit(chat.id, e.target.value)}
                    onBlur={() => setEditingChatId(null)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        setEditingChatId(null);
                      }
                    }}
                    className={`flex-grow bg-transparent border-b text-sm font-medium focus:outline-none ${
                      isDarkMode ? 'border-gray-400 text-white' : 'border-gray-500 text-gray-800'
                    }`}
                    autoFocus
                  />
                ) : (
                  <span onClick={() => {
                    setEditingChatId(chat.id);
                    // Use a timeout to ensure the input is rendered before focusing
                    setTimeout(() => titleInputRef.current?.focus(), 0);
                  }} className="text-sm font-medium truncate">{chat.title}</span>
                )}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteChat(chat.id);
                  }}
                  className={`p-1 rounded-full transition-colors duration-200 ${
                    activeChatId === chat.id
                      ? 'text-white hover:bg-blue-700'
                      : (isDarkMode ? 'text-gray-400 hover:bg-gray-600' : 'text-gray-500 hover:bg-gray-300')
                  }`}
                  title="Sohbeti Sil"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Ana Sohbet Ekranı */}
        <div className="flex flex-col flex-grow">
          {/* Sohbet başlığı ve kontrol butonları */}
          <div
            className={`flex justify-between items-center p-4 text-white font-bold tracking-wide transition-colors duration-300 relative rounded-tl-2xl rounded-bl-2xl md:rounded-l-none`}
            style={{
              fontFamily: "'Poppins', sans-serif",
              background: isDarkMode
                ? 'linear-gradient(to right, #2563eb, #1e3a8a)'
                : 'linear-gradient(to right, #0d9488, #0ea5e9)',
            }}
          >
            {/* Logo ve başlık */}
            <div className="flex items-center space-x-2">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-white">
                <path d="M12 2l-5 5h10l-5-5z" />
                <path d="M12 22l-5-5h10l-5 5z" />
                <path d="M22 12l-5-5v10l5-5z" />
                <path d="M2 12l5-5v10l-5-5z" />
                <circle cx="12" cy="12" r="3" />
              </svg>
              {isEditingTitle ? (
                <input
                  type="text"
                  value={currentChatTitle}
                  onChange={handleTitleEdit}
                  onBlur={() => setIsEditingTitle(false)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      setIsEditingTitle(false);
                    }
                  }}
                  className="bg-transparent border-b border-white text-sm font-bold focus:outline-none"
                  autoFocus
                />
              ) : (
                <span onClick={() => setIsEditingTitle(true)} className="text-sm cursor-pointer hover:underline">{currentChatTitle}</span>
              )}
            </div>

            {/* Menü ve Dark/Light Mod butonu */}
            <div className="flex items-center space-x-2">
              <button
                onClick={handleNewChat}
                className={`text-white text-sm font-semibold p-2 rounded-lg hover:bg-white hover:bg-opacity-20 transition-all duration-300`}
                title="Sohbeti Temizle"
              >
                Sohbeti Temizle
              </button>
              <button
                onClick={toggleDarkMode}
                className="p-2 rounded-full hover:bg-white hover:bg-opacity-20 transition-all duration-300"
                title="Tema Değiştir"
              >
                {isDarkMode ? <Sun className="w-5 h-5 text-yellow-300" /> : <Moon className="w-5 h-5 text-white" />}
              </button>
            </div>
          </div>

          {/* Mesajların görüntülendiği alan */}
          <div className={`flex flex-col flex-grow p-4 overflow-y-auto space-y-4 transition-colors duration-300 ${isDarkMode ? 'bg-gray-900' : 'bg-white'}`} style={{ fontFamily: "'Poppins', sans-serif" }}>
            {messages.map((message) => (
              <div key={message.id} className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'} animate-fadeIn`}>
                <div
                  className={`flex flex-col p-3 rounded-2xl max-w-[80%] break-words shadow-sm transition-colors duration-300 ${
                    message.sender === 'user'
                      ? (isDarkMode ? 'bg-gray-800 text-gray-200' : 'bg-blue-100 text-gray-800') + ' rounded-br-md'
                      : (isDarkMode ? 'bg-gray-700 text-gray-200' : 'bg-gray-100 text-gray-800') + ' rounded-bl-md'
                  }`}
                >
                  {/* Bot mesajları için özel görselleştirme */}
                  {message.sender === 'bot' && typeof message.text === 'object' ? (
                    renderRichResponse(message.text)
                  ) : (
                    <span className="text-sm">{message.text}</span>
                  )}
                </div>
              </div>
            ))}
            {/* Yükleniyor durumu */}
            {isLoading && (
              <div className="flex justify-start animate-fadeIn">
                <div className={`flex items-center space-x-2 p-3 rounded-xl shadow-sm transition-colors duration-300 ${isDarkMode ? 'bg-gray-700 text-gray-200' : 'bg-gray-100 text-gray-800'}`}>
                  <svg
                    className="w-5 h-5 text-indigo-500 animate-spin"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    ></path>
                  </svg>
                  <span className="text-sm">Yanıt hazırlanıyor...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Mesaj gönderme formu */}
          <div className={`p-4 border-t transition-colors duration-300 rounded-b-2xl ${isDarkMode ? 'bg-gray-900 border-gray-700' : 'bg-gray-100 border-gray-200'}`}>
            <div className="max-w-3xl mx-auto">
              <form onSubmit={handleSendMessage} className="flex flex-col sm:flex-row space-y-2 sm:space-y-0 sm:space-x-2">
                <input
                  type="text"
                  className={`flex-grow p-3 border rounded-full text-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all duration-300 ${isDarkMode ? 'bg-gray-800 text-gray-200 border-gray-700' : 'bg-white border-gray-300'}`}
                  placeholder="İhracat yapmak istediğiniz ürün adını girin..."
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                />
                <button
                  type="submit"
                  className={`p-3 rounded-full text-white text-sm font-semibold flex items-center justify-center transition-all duration-300 transform ${
                    isLoading
                      ? 'bg-gray-400 cursor-not-allowed'
                      : isDarkMode
                        ? 'bg-blue-600 hover:bg-blue-700 focus:ring-blue-500'
                        : 'bg-blue-500 hover:bg-blue-600 focus:ring-blue-500'
                  } focus:outline-none focus:ring-2 hover:scale-105`}
                  disabled={isLoading}
                >
                  <Sparkles className="w-5 h-5" />
                  <span className="ml-2 hidden sm:block">{isLoading ? 'Gönderiliyor...' : 'Öner'}</span>
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
