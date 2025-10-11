<?php
require_once "config.php";

// Eğer kullanıcı zaten giriş yapmışsa, ana sayfaya yönlendir
if(isset($_SESSION["loggedin"]) && $_SESSION["loggedin"] === true){
    header("location: index.php");
    exit;
}

$username = $password = "";
$username_err = $password_err = $login_err = "";

if($_SERVER["REQUEST_METHOD"] == "POST"){

    if(empty(trim($_POST["username"]))){
        $username_err = "Lütfen kullanıcı adınızı girin.";
    } else{
        $username = trim($_POST["username"]);
    }
    
    if(empty(trim($_POST["password"]))){
        $password_err = "Lütfen şifrenizi girin.";
    } else{
        $password = trim($_POST["password"]);
    }
    
    if(empty($username_err) && empty($password_err)){
        $sql = "SELECT id, username, password_hash FROM admins WHERE username = ?";
        
        if($stmt = $mysqli->prepare($sql)){
            $stmt->bind_param("s", $param_username);
            $param_username = $username;
            
            if($stmt->execute()){
                $stmt->store_result();
                
                if($stmt->num_rows == 1){                    
                    $stmt->bind_result($id, $username, $hashed_password);
                    if($stmt->fetch()){
                        if(password_verify($password, $hashed_password)){
                            session_start();
                            
                            $_SESSION["loggedin"] = true;
                            $_SESSION["id"] = $id;
                            $_SESSION["username"] = $username;                            
                            
                            header("location: index.php");
                        } else{
                            $login_err = "Geçersiz kullanıcı adı veya şifre.";
                        }
                    }
                } else{
                    $login_err = "Geçersiz kullanıcı adı veya şifre.";
                }
            } else{
                echo "Bir şeyler ters gitti. Lütfen daha sonra tekrar deneyin.";
            }
            $stmt->close();
        }
    }
    $mysqli->close();
}
?>
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lisans Yönetimi - Giriş</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="style.css">
    <link rel="stylesheet" href="https://unpkg.com/lucide@latest/dist/umd/lucide.min.js">
</head>
<body>
    <div class="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-blue-900/20 via-transparent to-transparent"></div>
        <div class="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_left,_var(--tw-gradient-stops))] from-purple-900/20 via-transparent to-transparent"></div>
        
        <div class="relative w-full max-w-md">
          <div class="bg-slate-800/50 backdrop-blur-xl rounded-2xl shadow-2xl border border-slate-700/50 p-8">
            <div class="text-center mb-8">
              <div class="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-purple-600 mb-4">
                <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-package"><path d="m7.5 4.27 9 5.15"/><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/></svg>
              </div>
              <h1 class="text-3xl font-bold text-white mb-2">Lisans Yönetimi</h1>
              <p class="text-slate-400 text-sm">Yönetim paneline hoş geldiniz</p>
            </div>
            
            <?php 
            if(!empty($login_err)){
                echo '<div class="bg-red-500/10 text-red-400 border border-red-500/20 p-3 rounded-lg mb-4 text-sm">' . $login_err . '</div>';
            }        
            ?>

            <form action="<?php echo htmlspecialchars($_SERVER["PHP_SELF"]); ?>" method="post" class="space-y-4">
              <div>
                <label class="block text-sm font-medium text-slate-300 mb-2">Kullanıcı Adı</label>
                <input name="username" type="text" class="w-full px-4 py-3 bg-slate-900/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition <?php echo (!empty($username_err)) ? 'border-red-500' : ''; ?>" value="<?php echo $username; ?>" placeholder="admin">
              </div>
              
              <div>
                <label class="block text-sm font-medium text-slate-300 mb-2">Şifre</label>
                <input name="password" type="password" class="w-full px-4 py-3 bg-slate-900/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition <?php echo (!empty($password_err)) ? 'border-red-500' : ''; ?>" placeholder="••••••••">
              </div>
              
              <button type="submit" class="w-full bg-gradient-to-r from-blue-500 to-purple-600 text-white py-3 rounded-lg font-semibold hover:from-blue-600 hover:to-purple-700 transition transform hover:scale-[1.02] shadow-lg">
                Giriş Yap
              </button>
            </form>
          </div>
        </div>
      </div>
</body>
</html>